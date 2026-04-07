from nonebot import get_driver
from nonebot.adapters.onebot.v11 import Bot
from fastapi import Request
from nonebot import get_app
import json
import os
import logging
import hashlib

app = get_app()
driver = get_driver()

SUBSCRIBE_FILE = "emby_subscribe.json"
LAST_MESSAGE_FILE = "emby_last_message.json"

def load_subscribe():
    if not os.path.exists(SUBSCRIBE_FILE):
        return {}
    with open(SUBSCRIBE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def load_last_message():
    """加载最后推送的消息记录"""
    if not os.path.exists(LAST_MESSAGE_FILE):
        return {}
    try:
        with open(LAST_MESSAGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_last_message(last_messages):
    """保存最后推送的消息记录"""
    with open(LAST_MESSAGE_FILE, "w", encoding="utf-8") as f:
        json.dump(last_messages, f, ensure_ascii=False, indent=2)

def get_message_hash(message):
    """计算消息的哈希值"""
    return hashlib.md5(message.encode("utf-8")).hexdigest()

@app.post("/emby/webhook")
async def emby_webhook(request: Request):
    try:
        data = await request.json()
        logging.info(f"收到 webhook 数据: {data}")
        name = data.get("name")
        subscribe_dict = load_subscribe()

        # 如果没有 name 字段，尝试用 Server.Name 匹配
        if not name:
            server = data.get("Server", {})
            server_name = server.get("Name")
            if not server_name:
                return {"error": "缺少 emby 名称参数，也没有 Server.Name"}
            name = server_name

        emby_info = subscribe_dict.get(name)
        if not emby_info:
            return {"error": f"Emby 名称 {name} 不存在"}
        emby_host = emby_info["url"]
        group_ids = emby_info["groups"]

        # 组装消息（示例，实际可根据你的需求调整）
        title = data.get("Title", "未知通知")
        description = data.get("Description", "")
        item = data.get("Item", {})
        image_url = ""
        item_id = item.get("Id")
        image_tags = item.get("ImageTags", {})
        if "Primary" in image_tags and item_id:
            image_url = f"{emby_host}/Items/{item_id}/Images/Primary?maxWidth=640"
        if not image_url:
            series_id = item.get("SeriesId")
            series_image_tags = item.get("SeriesImageTags", {})
            if series_id and "Primary" in series_image_tags:
                image_url = f"{emby_host}/Items/{series_id}/Images/Primary?maxWidth=640"

        # 组装消息
        series_name = item.get("SeriesName", title)
        episode_number = item.get("IndexNumber", "")
        episode_title = item.get("Name", "")
        runtime_ticks = item.get("RunTimeTicks", 0)
        runtime_minutes = int(runtime_ticks / 10_000_000 / 60) if runtime_ticks else ""
        overview = item.get("Overview", "")

        msg = f"Emby服务器：{name}\n"
        msg += f"🎞️ 《{series_name}》更新啦\n"
        msg += f"📌 第{episode_number}集：{episode_title}\n"
        msg += f"⏱️ 时长：{runtime_minutes}分钟\n"
        msg += f"{overview}\n"
        if image_url:
            msg += f"[CQ:image,file={image_url}]"

        # 检查消息是否与上次相同
        last_messages = load_last_message()
        current_msg_hash = get_message_hash(msg)
        
        last_msg_hash = last_messages.get(name)
        if last_msg_hash == current_msg_hash:
            logging.info(f"消息与上次相同，跳过推送")
            return {"status": "skipped", "reason": "消息重复", "groups": group_ids}
        
        # 更新最后推送的消息记录
        last_messages[name] = current_msg_hash
        save_last_message(last_messages)

        bot: Bot = list(driver.bots.values())[0]
        for group_id in group_ids:
            try:
                await bot.send_group_msg(group_id=group_id, message=msg)
                logging.info(f"已推送到群 {group_id}")
            except Exception as e:
                logging.error(f"推送到群 {group_id} 失败: {e}")

        return {"status": "ok", "groups": group_ids}
    except Exception as e:
        return {"error": str(e)}
