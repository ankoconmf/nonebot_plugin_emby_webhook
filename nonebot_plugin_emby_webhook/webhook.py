from nonebot import get_driver
from nonebot.adapters.onebot.v11 import Bot
from fastapi import Request
from nonebot import get_app
import json
import os

app = get_app()
driver = get_driver()

SUBSCRIBE_FILE = "emby_subscribe.json"

def load_subscribe():
    if not os.path.exists(SUBSCRIBE_FILE):
        return []
    with open(SUBSCRIBE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

@app.post("/emby/webhook")
async def emby_webhook(request: Request):
    try:
        data = await request.json()
        item = data.get("Item", {})
        item_id = item.get("Id")
        image_tags = item.get("ImageTags", {})

        # 提取所需字段
        series_name = item.get("SeriesName", "未知剧集")
        episode_number = item.get("IndexNumber", 0)
        episode_name = item.get("Name", "未知标题")
        runtime_ticks = item.get("RunTimeTicks", 0)

        # 将 ticks 转为分钟（1 tick = 10000 毫秒）
        runtime_minutes = int(runtime_ticks / 10_000_000 / 60)

        # 生成封面图地址
        emby_host = "http://127.0.0.1:8096"  # ← 改为你的 Emby 地址
        image_url = ""
        if "Primary" in image_tags and item_id:
            image_url = f"{emby_host}/Items/{item_id}/Images/Primary?maxWidth=640"

        # 组装消息
        msg = (
            f"🎞️ 《{series_name}》更新啦\n"
            f"📌 第{episode_number}集：{episode_name}\n"
            f"⏱️ 时长：{runtime_minutes} 分钟\n"
        )
        if image_url:
            msg += f"\n[CQ:image,file={image_url}]"

        bot: Bot = list(driver.bots.values())[0]
        group_ids = load_subscribe()

        for group_id in group_ids:
            await bot.send_group_msg(group_id=group_id, message=msg)

        return {"status": "ok", "groups": group_ids}
    except Exception as e:
        return {"error": str(e)}
