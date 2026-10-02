from nonebot import get_driver, logger
from nonebot.adapters.onebot.v11 import Bot
from fastapi import Request
from nonebot import get_app
import json
import os
import hashlib
import re
from html import unescape
import html
from urllib.parse import quote
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


# 简介字符上限。QQ 单条消息长度有限，超过这里按句子截断并补省略号；
# 想完整显示就把数字调大（Emby/TMDB 的长简介通常几百字）。
OVERVIEW_MAX_LENGTH = 1000

_SENTENCE_ENDS = "。！？!?….；;"


def format_overview(text, max_length=OVERVIEW_MAX_LENGTH):
    """整理简介：成段的连续空白还原成换行，超长时按句子截断并加省略号"""
    text = (text or "").strip()

    if not text:
        return ""

    # Emby/TMDB 的简介用连续空格或换行分段，原样发出去会糊成一整段
    text = re.sub(r"[ \t]*\n[ \t]*", "\n", text)
    text = re.sub(r"[ \t]{2,}", "\n", text)
    text = re.sub(r"\n{2,}", "\n", text).strip()

    if len(text) <= max_length:
        return text

    clipped = text[:max_length]

    # 尽量截在句子结尾，避免停在半个句子上
    cut = max(clipped.rfind(char) for char in _SENTENCE_ENDS)

    if cut > max_length // 2:
        clipped = clipped[:cut + 1]

    return f"{clipped.rstrip()}……"


def make_async_client(**kwargs):
    """构造 httpx 异步客户端。

    环境变量 no_proxy 里含 [::1] 这类带方括号的条目时，httpx 解析环境代理
    会在构造阶段直接抛 InvalidURL，导致请求全都拿不到结果。这种情况退化为
    直连，并在日志里说明。
    """
    try:
        return httpx.AsyncClient(**kwargs)
    except Exception as e:
        logger.warning(
            f"读取系统代理配置失败（{e}），本次改用直连（忽略环境代理）"
        )
        return httpx.AsyncClient(trust_env=False, **kwargs)


async def image_exists(url):
    """检查图片 URL 是否真实存在（避免推送 404 坏图）"""
    try:
        async with make_async_client(
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


# Bangumi 接口与请求头（Bangumi 要求带 User-Agent，否则可能被拒）
BANGUMI_API = "https://api.bgm.tv"
BANGUMI_HEADERS = {
    "User-Agent": (
        "nonebot-plugin-emby-webhook "
        "(https://github.com/ankoconmf/nonebot_plugin_emby_webhook)"
    )
}

# 按“剧名 + 季号”缓存查询结果，同一部番反复推送时不再重复请求
_bangumi_cache = {}

# 找不到对应季度条目时，退回用系列主条目（通常就是第一季）的评分，
# 并在消息里标注「第一季」以免和当季分数混淆。关掉则改为不显示评分行。
BANGUMI_FALLBACK_TO_SERIES = True

_CN_NUMBERS = "零一二三四五六七八九"
_CN_DIGITS = {char: index for index, char in enumerate(_CN_NUMBERS) if index}


def to_chinese_number(number):
    """1-99 转中文数字，用于拼「第三季」这类搜索词"""
    if not isinstance(number, int) or number < 1 or number > 99:
        return ""

    if number < 10:
        return _CN_NUMBERS[number]

    tens, ones = divmod(number, 10)
    text = "十" if tens == 1 else f"{_CN_NUMBERS[tens]}十"

    return text if ones == 0 else f"{text}{_CN_NUMBERS[ones]}"


def chinese_to_int(text):
    """「三」「十二」「二十一」转成整数，解析失败返回 None"""
    text = (text or "").strip()

    if not text:
        return None

    if "十" not in text:
        return _CN_DIGITS.get(text)

    left, _, right = text.partition("十")

    if (left and left not in _CN_DIGITS) or (right and right not in _CN_DIGITS):
        return None

    tens = _CN_DIGITS[left] if left else 1
    ones = _CN_DIGITS[right] if right else 0

    return tens * 10 + ones


def parse_season_number(*values):
    """从季号字段或「第 3 季」这类文本里取季号，取不到返回 None"""
    for value in values:
        if value is None or isinstance(value, bool):
            continue

        if isinstance(value, int):
            if value > 0:
                return value
            continue

        text = str(value).strip()

        if not text:
            continue

        digits = re.search(r"\d+", text)

        if digits:
            number = int(digits.group())
            if number > 0:
                return number
            continue

        chinese = re.search(r"[一二三四五六七八九十]+", text)

        if chinese:
            number = chinese_to_int(chinese.group())
            if number:
                return number

    return None


def ordinal(number):
    """3 -> 3rd，用于匹配「3rd Season」"""
    if 10 <= number % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(number % 10, "th")

    return f"{number}{suffix}"


def season_matches(text, season):
    """条目名里是否标了指定季号（第3季 / 第3期 / 第三季 / Season 3 / 3rd Season）"""
    if not text or not season or season < 2:
        return False

    normalized = re.sub(r"\s+", "", str(text)).lower()

    markers = [
        f"第{season}季",
        f"第{season}期",
        f"第{season}部",
        f"season{season}",
        f"{ordinal(season)}season",
    ]

    chinese = to_chinese_number(season)

    if chinese:
        markers += [
            f"第{chinese}季",
            f"第{chinese}期",
            f"第{chinese}部",
        ]

    return any(marker in normalized for marker in markers)


def build_bangumi_keywords(keyword, season):
    """按优先级给出候选搜索词，季度大于 1 时把季号并进去"""
    keywords = []

    if season and season > 1:
        keywords.append(f"{keyword} 第{season}季")

        chinese = to_chinese_number(season)

        if chinese:
            keywords.append(f"{keyword} 第{chinese}季")

        keywords.append(f"{keyword} Season {season}")

    keywords.append(keyword)

    return keywords


async def fetch_bangumi_info(keyword, season=None):
    """用番剧名去 Bangumi 搜索条目（无需 API key），返回封面与评分。

    带季号时优先找对应季度的条目并校验条目名里的季号，避免整部作品的第 2、
    3 季都拿到第一季（主条目）的评分；找不到当季条目时按 BANGUMI_FALLBACK_TO_SERIES
    退回主条目评分并标注，关掉开关则不显示评分。
    """
    keyword = (keyword or "").strip()

    if not keyword:
        return {}

    season = season if season and season > 1 else None

    cache_key = (keyword, season)

    if cache_key in _bangumi_cache:
        return _bangumi_cache[cache_key]

    series_info = {}

    for candidate in build_bangumi_keywords(keyword, season):
        info = await _request_bangumi_info(candidate)

        if not info:
            continue

        if not season:
            # 单片（电影）或第一季：主条目就是它本身
            _bangumi_cache[cache_key] = info
            return info

        entry_name = f"{info.get('name') or ''} {info.get('name_original') or ''}"

        if season_matches(entry_name, season):
            _bangumi_cache[cache_key] = info
            return info

        # 不带季号的候选命中的是系列主条目，留作兜底
        if candidate == keyword:
            series_info = info

    if season and series_info and BANGUMI_FALLBACK_TO_SERIES:
        series_info["first_season_fallback"] = True
        _bangumi_cache[cache_key] = series_info

        logger.info(
            f"Bangumi 没有第{season}季的条目，退回主条目"
            f"《{series_info.get('name')}》的评分: {keyword}"
        )

        return series_info

    # 只在有结果时缓存，避免网络临时故障或新番未建条目被长期记住
    if season:
        logger.info(
            f"Bangumi 没有第{season}季的条目，本条推送不显示评分: {keyword}"
        )

    return {}


async def _request_bangumi_info(keyword):
    search_url = (
        f"{BANGUMI_API}/search/subject/"
        f"{quote(keyword)}?type=2&responseGroup=small&max_results=1"
    )

    try:
        async with make_async_client(timeout=5) as client:
            resp = await client.get(
                search_url,
                headers=BANGUMI_HEADERS,
                follow_redirects=True,
            )

            if resp.status_code != 200:
                logger.info(
                    f"Bangumi 搜索无结果: {keyword} "
                    f"(status={resp.status_code})"
                )
                return {}

            items = (resp.json().get("list")) or []

            if not items:
                logger.info(f"Bangumi 未找到条目: {keyword}")
                return {}

            top = items[0]

            images = top.get("images") or {}

            image_url = (
                images.get("large")
                or images.get("common")
                or images.get("medium")
                or ""
            )

            # bgm 返回的图片链接是 http，换成 https 更兼容
            if image_url.startswith("http://"):
                image_url = "https://" + image_url[len("http://"):]

            name = top.get("name_cn") or top.get("name") or ""

            # 评分只在新版 v0 详情接口里，search 接口不返回
            score, votes = await _fetch_bangumi_rating(
                client, top.get("id")
            )

            logger.info(
                f"Bangumi 命中搜索「{keyword}」→《{name}》"
                f" 封面: {image_url or '无'}"
                f" 评分: {score if score else '无'}"
            )

            return {
                "id": top.get("id"),
                "name": name,
                "name_original": top.get("name") or "",
                "image": image_url,
                "score": score,
                "votes": votes,
            }
    except Exception:
        logger.opt(exception=True).warning(
            f"Bangumi 搜索失败: {keyword}"
        )
        return {}


async def _fetch_bangumi_rating(client, subject_id):
    """从 Bangumi v0 详情接口取评分，返回 (评分, 评分人数)"""
    if not subject_id:
        return None, 0

    try:
        resp = await client.get(
            f"{BANGUMI_API}/v0/subjects/{subject_id}",
            headers=BANGUMI_HEADERS,
            follow_redirects=True,
        )

        if resp.status_code != 200:
            logger.info(
                f"Bangumi 详情获取失败: {subject_id} "
                f"(status={resp.status_code})"
            )
            return None, 0

        rating = resp.json().get("rating") or {}

        score = rating.get("score")
        votes = rating.get("total") or 0

        if not score:
            return None, 0

        return round(float(score), 1), int(votes)
    except Exception:
        logger.opt(exception=True).warning(
            f"Bangumi 评分获取失败: {subject_id}"
        )
        return None, 0


def format_bangumi_score(info):
    """把 Bangumi 评分格式化成消息行，没有评分时返回空串"""
    info = info or {}

    score = info.get("score")

    if not score:
        return ""

    votes = info.get("votes") or 0

    detail = f"{votes}人评分" if votes else ""

    # 退回到主条目（第一季）时标注出来，避免误当成当季评分
    if info.get("first_season_fallback"):
        detail = f"{detail}·第一季" if detail else "第一季"

    if detail:
        return f"⭐ Bangumi评分：{score}分（{detail}）"

    return f"⭐ Bangumi评分：{score}分"


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

                # webhook 已带 SeriesPrimaryImageTag 时说明剧集海报存在，
                # 直接使用，避免多余的 HTTP 请求（网络失败会误判为没图）
                if item.get("SeriesPrimaryImageTag"):
                    image_url = series_image_url
                elif await image_exists(series_image_url):
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

        overview = format_overview(
            html.unescape(item.get("Overview", ""))
        )

        # Bangumi：查一次拿评分，Emby 没有海报时顺带用它兜底封面
        if item_type == "Movie":
            bangumi_keyword = item_name
            bangumi_season = None
        else:
            bangumi_keyword = html.unescape(
                item.get("SeriesName", "")
            )
            # 第 3 季要查第 3 季的条目，只给剧名会命中第一季（主条目）
            bangumi_season = parse_season_number(
                item.get("ParentIndexNumber"),
                item.get("SeasonName"),
            )

        bangumi_info = await fetch_bangumi_info(
            bangumi_keyword,
            bangumi_season,
        )

        if not image_url:
            image_url = bangumi_info.get("image", "")

        bangumi_line = format_bangumi_score(bangumi_info)

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

            season_number = item.get("ParentIndexNumber")

            # 特别篇/OVA 的季号为 0（falsy），此时用 SeasonName（如「特别篇」）
            season_name = html.unescape(item.get("SeasonName", ""))

            msg = f"Emby服务器：{name}\n"
            msg += f"🎞️ 《{series_name}》更新啦\n"
            if season_number:
                msg += f"📌 第{season_number}季 第{episode_number}集：{episode_title}\n"
            elif season_name:
                msg += f"📌 {season_name} 第{episode_number}集：{episode_title}\n"
            else:
                msg += f"📌 第{episode_number}集：{episode_title}\n"

        if bangumi_line:
            msg += f"{bangumi_line}\n"

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

        overview = format_overview(
            html.unescape(data.get("Overview", ""))
        )

        # 图片
        item_id = data.get("ItemId")

        image_url = ""

        if item_id:
            image_url = (
                f"{jellyfin_host}/Items/{item_id}/Images/Primary"
                f"?maxWidth=640"
            )

        # Bangumi：查一次拿评分，Jellyfin 没有 ItemId 时顺带兜底封面
        if item_type == "Movie":
            bangumi_keyword = item_name
            bangumi_season = None
        else:
            bangumi_keyword = series_name
            # 第 3 季要查第 3 季的条目，只给剧名会命中第一季（主条目）
            bangumi_season = parse_season_number(
                data.get("SeasonNumber00"),
                data.get("SeasonNumber"),
            )

        bangumi_info = await fetch_bangumi_info(
            bangumi_keyword,
            bangumi_season,
        )

        if not image_url:
            image_url = bangumi_info.get("image", "")

        bangumi_line = format_bangumi_score(bangumi_info)

        # 组装消息
        msg = f"Jellyfin服务器：{name}\n"
        msg += f"🎬 《{series_name}》更新啦\n"
        msg += f"📌 {title}\n"

        if bangumi_line:
            msg += f"{bangumi_line}\n"

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