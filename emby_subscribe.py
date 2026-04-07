from nonebot.plugin import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent
import json
import os

SUBSCRIBE_FILE = "emby_subscribe.json"

def load_subscribe():
    if not os.path.exists(SUBSCRIBE_FILE):
        return {}
    with open(SUBSCRIBE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_subscribe(subscribe_dict):
    with open(SUBSCRIBE_FILE, "w", encoding="utf-8") as f:
        json.dump(subscribe_dict, f, ensure_ascii=False, indent=2)

subscribe = on_command("订阅emby")
unsubscribe = on_command("取消订阅emby")
addemby = on_command("添加emby")
deleteemby = on_command("删除emby")

@subscribe.handle()
async def _(event: GroupMessageEvent):
    text = event.get_plaintext().strip()
    # 去掉“订阅emby”前缀
    if text.startswith("订阅emby"):
        text = text[len("订阅emby"):].strip()
    args = text.split()
    if not args:
        await subscribe.finish("用法：订阅emby 名称")
    name = args[0]
    group_id = event.group_id
    subscribe_dict = load_subscribe()
    if name not in subscribe_dict:
        await subscribe.finish(f"Emby 名称 {name} 不存在。")
    if group_id in subscribe_dict[name]["groups"]:
        await subscribe.finish(f"本群已订阅 Emby({name}) 更新通知~")
    subscribe_dict[name]["groups"].append(group_id)
    save_subscribe(subscribe_dict)
    await subscribe.finish(f"✅ 本群已成功订阅 Emby({name}) 更新！")

@unsubscribe.handle()
async def _(event: GroupMessageEvent):
    text = event.get_plaintext().strip()
    # 去掉“取消订阅emby”前缀
    if text.startswith("取消订阅emby"):
        text = text[len("取消订阅emby"):].strip()
    args = text.split()
    if not args:
        await unsubscribe.finish("用法：取消订阅emby 名称")
    name = args[0]
    group_id = event.group_id
    subscribe_dict = load_subscribe()
    if name not in subscribe_dict:
        await unsubscribe.finish(f"Emby 名称 {name} 不存在。")
    if group_id not in subscribe_dict[name]["groups"]:
        await unsubscribe.finish(f"本群尚未订阅 Emby({name}) 更新。")
    subscribe_dict[name]["groups"].remove(group_id)
    save_subscribe(subscribe_dict)
    await unsubscribe.finish(f"❎ 本群已取消 Emby({name}) 更新订阅。")

@addemby.handle()
async def _(event: GroupMessageEvent):
    # 获取消息内容并去除命令前缀
    text = event.get_plaintext().strip()
    # 去掉“添加emby”前缀
    if text.startswith("添加emby"):
        text = text[len("添加emby"):].strip()
    args = text.split()
    if len(args) < 2:
        await addemby.finish("用法：添加emby 名称 地址")
    name, url = args[0], args[1]
    subscribe_dict = load_subscribe()
    if name in subscribe_dict:
        await addemby.finish(f"名称 {name} 已存在。")
    subscribe_dict[name] = {"url": url, "groups": []}
    save_subscribe(subscribe_dict)
    await addemby.finish(f"已添加 Emby：{name}，地址：{url}")

@deleteemby.handle()
async def _(event: GroupMessageEvent):
    text = event.get_plaintext().strip()
    # 去掉“删除emby”前缀
    if text.startswith("删除emby"):
        text = text[len("删除emby"):].strip()
    args = text.split()
    if not args:
        await deleteemby.finish("用法：删除emby 名称")
    name = args[0]
    subscribe_dict = load_subscribe()
    if name not in subscribe_dict:
        await deleteemby.finish(f"Emby 名称 {name} 不存在。")
    del subscribe_dict[name]
    save_subscribe(subscribe_dict)
    await deleteemby.finish(f"已删除 Emby：{name}")
