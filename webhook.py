from nonebot import get_driver, logger
from nonebot.adapters.onebot.v11 import Bot
from fastapi import Request
from nonebot import get_app
import json
import os
import hashlib
from html import unescape
import html
import httpx

app = get_app()
driver = get_driver()

SUBSCRIBE_FILE = "emby_subscribe.json"
LAST_MESSAGE_FILE = "emby_last_message.json"

# 服务器类型
SERVER_TYPE_EMBY = "emby"
SERVER_TYPE_JELLYFIN = "jellyfin"


def load_subscribe():
    if not os.path.exists(SUBSCRIBE_FILE):
        return {}

    try:
        with open(SUBSCRIBE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.opt(exception=True).error("读取订阅配置失败")
        return {}


def load_last_messages():
    """加载最后推送的消息记录（保留最后5条）"""
    if not os.path.exists(LAST_MESSAGE_FILE):
        return {}

    try:
        with open(LAST_MESSAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        logger.opt(exception=True).error("读取历史消息失败")
        return {}


def save_last_messages(last_messages):
    """保存最后推送的消息记录（最多保留5条）"""
    try:
        with open(LAST_MESSAGE_FILE, "w", encoding="utf-8") as f:
            json.dump(last_messages, f, ensure_ascii=False, indent=2)
    except Exception:
        logger.opt(exception=True).error("保存历史消息失败")


def add_message_to_history(name, msg_hash, last_messages, max_history=5):
    """将消息哈希添加到历史记录"""
    if name not in last_messages:
        last_messages[name] = []

    last_messages[name].insert(0, msg_hash)

    if len(last_messages[name]) > max_history:
        last_messages[name] = last_messages[name][:max_history]


def get_message_hash(message):
    """计算消息哈希"""
    return hashlib.md5(message.encode("utf-8")).hexdigest()


def detect_server_type(data):
    """检测数据来自 Emby 还是 Jellyfin"""
    if data.get("name") or (
        isinstance(data.get("Server"), dict)
        and data.get("Server", {}).get("Name")
    ):
        return SERVER_TYPE_EMBY

    if data.get("ServerName"):
        return SERVER_TYPE_JELLYFIN

    return None


def parse_runtime(runtime_ticks):
    """Ticks 转分钟"""
    if not runtime_ticks:
        return ""

    try:
        runtime_ticks = int(runtime_ticks)
        runtime_minutes = int(runtime_ticks / 10_000_000 / 60)
        return f"{runtime_minutes}分钟"
    except Exception:
        return ""


async def image_exists(url):
    """检查图片 URL 是否真实存在（避免推送 404 坏图）"""
    try:
        async with httpx.AsyncClient(
            timeout=5,
            verify=False,
        ) as client:
            resp = await client.get(
                url,
                follow_redirects=True,
            )

            content_type = resp.headers.get("Content-Type", "")

            return (
                resp.status_code == 200
                and content_type.startswith("image/")
            )
    except Exception:
        logger.opt(exception=True).warning(
            f"检查图片存在性失败: {url}"
        )
        return False


async def send_notification(msg, name, subscribe_dict):
    """发送通知到订阅群组"""
    server_info = subscribe_dict.get(name)

    if not server_info:
        logger.error(f"send_notification: 服务器 {name} 不存在")
        return {"error": f"服务器 {name} 不存在"}

    group_ids = server_info.get("groups", [])

    logger.info(
        f"send_notification: 服务器 {name} 订阅群组: {group_ids}"
    )

    if not group_ids:
        logger.warning(
            f"send_notification: 服务器 {name} 没有订阅群组"
        )
        return {
            "status": "no_subscribers",
            "reason": "没有群组订阅此服务器",
        }

    # 去重
    last_messages = load_last_messages()

    current_msg_hash = get_message_hash(msg)

    message_history = last_messages.get(name, [])

    if current_msg_hash in message_history:
        logger.info("send_notification: 消息重复，跳过推送")
        return {
            "status": "skipped",
            "reason": "消息重复",
            "groups": group_ids,
        }

    add_message_to_history(
        name,
        current_msg_hash,
        last_messages,
    )

    save_last_messages(last_messages)

    bots = list(driver.bots.values())

    if not bots:
        logger.error("没有可用 Bot")
        return {"error": "没有可用 Bot"}

    bot: Bot = bots[0]

    for group_id in group_ids:
        try:
            await bot.send_group_msg(
                group_id=group_id,
                message=msg,
            )

            logger.info(f"已推送到群 {group_id}")

        except Exception:
            logger.opt(exception=True).error(
                f"推送到群 {group_id} 失败"
            )

    return {
        "status": "ok",
        "groups": group_ids,
    }


@app.post("/emby/webhook")
async def emby_webhook(request: Request):
    try:
        data = await request.json()

        logger.info(f"收到 Emby webhook 数据: {data}")

        name = data.get("name")

        subscribe_dict = load_subscribe()

        # 尝试从 Server.Name 获取
        if not name:
            server = data.get("Server", {})
            server_name = server.get("Name")

            if not server_name:
                return {
                    "error": "缺少 emby 名称参数，也没有 Server.Name"
                }

            name = server_name

        server_info = subscribe_dict.get(name)

        if not server_info:
            return {"error": f"Emby 名称 {name} 不存在"}

        if (
            server_info.get("type")
            and server_info.get("type") != SERVER_TYPE_EMBY
        ):
            return {"error": f"服务器 {name} 不是 Emby 类型"}

        emby_host = server_info.get("url", "")
        
        # 清理末尾的斜杠
        if emby_host.endswith("/"):
            emby_host = emby_host[:-1]

        # 提取信息
        title = html.unescape(
            data.get("Title", "未知通知")
        )

        item = data.get("Item", {})

        image_url = ""

        # 图片
        item_id = item.get("Id")

        image_tags = item.get("ImageTags", {})

        if "Primary" in image_tags and item_id:
            image_url = (
                f"{emby_host}/Items/{item_id}/Images/Primary"
                f"?maxWidth=640"
            )

        # 单集没图时，兜底用剧集海报
        if not image_url:
            series_id = item.get("SeriesId")

            if series_id:
                series_image_url = (
                    f"{emby_host}/Items/{series_id}/Images/Primary"
                    f"?maxWidth=640"
                )

                if await image_exists(series_image_url):
                    image_url = series_image_url
                else:
                    logger.info(
                        f"剧集 {series_id} 没有可用海报，跳过图片"
                    )

        # 类型：Movie（剧场版/电影）或 Episode（剧集）
        item_type = item.get("Type", "")

        item_name = html.unescape(
            item.get("Name", "")
        )

        original_title = html.unescape(
            item.get("OriginalTitle", "")
        )

        runtime_ticks = item.get(
            "RunTimeTicks",
            0,
        )

        runtime_str = parse_runtime(runtime_ticks)

        overview = html.unescape(
            item.get("Overview", "")
        )

        overview = overview[:300]

        # 组装
        if item_type == "Movie":
            # 剧场版/电影
            movie_name = item_name or title
            msg = f"Emby服务器：{name}\n"
            msg += f"🎬 剧场版《{movie_name}》更新啦\n"
            if original_title and original_title != movie_name:
                msg += f"📀 原名：{original_title}\n"

            year = item.get("ProductionYear", "")
            if year:
                msg += f"📅 年份：{year}\n"
        else:
            # 剧集
            series_name = html.unescape(
                item.get("SeriesName", title)
            )

            episode_number = item.get("IndexNumber", "?")

            episode_title = item_name

            season_number = item.get("ParentIndexNumber", "")

            msg = f"Emby服务器：{name}\n"
            msg += f"🎞️ 《{series_name}》更新啦\n"
            if season_number:
                msg += f"📌 第{season_number}季 第{episode_number}集：{episode_title}\n"
            else:
                msg += f"📌 第{episode_number}集：{episode_title}\n"

        if runtime_str:
            msg += f"⏱️ 时长：{runtime_str}\n"

        if overview:
            msg += f"{overview}\n"

        if image_url:
            msg += f"[CQ:image,file={image_url}]"

        return await send_notification(
            msg,
            name,
            subscribe_dict,
        )

    except Exception as e:
        logger.opt(exception=True).error(
            "Emby webhook 处理错误"
        )
        return {"error": str(e)}


@app.post("/jellyfin/webhook")
async def jellyfin_webhook(request: Request):
    try:
        data = await request.json()

        logger.info(f"收到 Jellyfin webhook 数据: {data}")

        name = data.get("ServerName")

        logger.info(f"Jellyfin ServerName: {name}")

        if not name:
            logger.error("缺少 Jellyfin 服务器名称")
            return {"error": "缺少 Jellyfin 服务器名称"}

        subscribe_dict = load_subscribe()

        logger.info(
            f"所有已配置的服务器: {list(subscribe_dict.keys())}"
        )

        server_info = subscribe_dict.get(name)

        if not server_info:
            logger.error(
                f"服务器名称 {name} 不存在，"
                f"已配置的: {list(subscribe_dict.keys())}"
            )

            return {"error": f"服务器名称 {name} 不存在"}

        logger.info(f"服务器信息: {server_info}")

        if (
            server_info.get("type")
            and server_info.get("type") != SERVER_TYPE_JELLYFIN
        ):
            logger.error(
                f"服务器 {name} 不是 Jellyfin 类型，"
                f"实际类型: {server_info.get('type')}"
            )

            return {"error": f"服务器 {name} 不是 Jellyfin 类型"}

        jellyfin_host = server_info.get("url", "")
        
        # 清理末尾的斜杠
        if jellyfin_host.endswith("/"):
            jellyfin_host = jellyfin_host[:-1]

        # 文本
        item_name = html.unescape(
            data.get("Name", "未知")
        )

        item_type = data.get("ItemType", "")

        series_name = html.unescape(
            data.get("SeriesName", item_name)
        )

        # 集数兼容
        if item_type == "Episode":
            season_number = (
                data.get("SeasonNumber00")
                or data.get("SeasonNumber")
                or "?"
            )

            episode_number = (
                data.get("EpisodeNumber00")
                or data.get("EpisodeNumber")
                or "?"
            )

            title = f"第{season_number}季 第{episode_number}集"

        else:
            title = item_name

        runtime_ticks = data.get("RunTimeTicks")

        runtime_str = parse_runtime(runtime_ticks)

        overview = html.unescape(
            data.get("Overview", "")
        )

        overview = overview[:300]

        # 图片
        item_id = data.get("ItemId")

        image_url = ""

        if item_id:
            image_url = (
                f"{jellyfin_host}/Items/{item_id}/Images/Primary"
                f"?maxWidth=640"
            )

        # 组装消息
        msg = f"Jellyfin服务器：{name}\n"
        msg += f"🎬 《{series_name}》更新啦\n"
        msg += f"📌 {title}\n"

        if runtime_str:
            msg += f"⏱️ 时长：{runtime_str}\n"

        if overview:
            msg += f"{overview}\n"

        if image_url:
            msg += f"[CQ:image,file={image_url}]"

        logger.info(f"组装的消息: {msg}")

        return await send_notification(
            msg,
            name,
            subscribe_dict,
        )

    except Exception as e:
        logger.opt(exception=True).error(
            "Jellyfin webhook 处理错误"
        )

        return {"error": str(e)}