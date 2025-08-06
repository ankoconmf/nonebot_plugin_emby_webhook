from nonebot.plugin import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent
import json
import os

SUBSCRIBE_FILE = "emby_subscribe.json"

def load_subscribe():
    if not os.path.exists(SUBSCRIBE_FILE):
        return []
    with open(SUBSCRIBE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_subscribe(group_ids):
    with open(SUBSCRIBE_FILE, "w", encoding="utf-8") as f:
        json.dump(group_ids, f)

subscribe = on_command("订阅emby")
unsubscribe = on_command("取消订阅emby")

@subscribe.handle()
async def _(event: GroupMessageEvent):
    group_id = event.group_id
    group_ids = load_subscribe()
    if group_id in group_ids:
        await subscribe.finish("本群已订阅 Emby 更新通知~")
    group_ids.append(group_id)
    save_subscribe(group_ids)
    await subscribe.finish("✅ 本群已成功订阅 Emby 更新！")

@unsubscribe.handle()
async def _(event: GroupMessageEvent):
    group_id = event.group_id
    group_ids = load_subscribe()
    if group_id not in group_ids:
        await unsubscribe.finish("本群尚未订阅 Emby 更新。")
    group_ids.remove(group_id)
    save_subscribe(group_ids)
    await unsubscribe.finish("❎ 本群已取消 Emby 更新订阅。")
