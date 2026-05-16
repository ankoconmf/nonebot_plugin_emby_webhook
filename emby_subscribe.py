from nonebot.plugin import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent
import json
import os

SUBSCRIBE_FILE = "emby_subscribe.json"

# 服务器类型常量
SERVER_TYPE_EMBY = "emby"
SERVER_TYPE_JELLYFIN = "jellyfin"

def load_subscribe():
    if not os.path.exists(SUBSCRIBE_FILE):
        return {}
    with open(SUBSCRIBE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_subscribe(subscribe_dict):
    with open(SUBSCRIBE_FILE, "w", encoding="utf-8") as f:
        json.dump(subscribe_dict, f, ensure_ascii=False, indent=2)

# Emby 相关命令
subscribe_emby = on_command("订阅emby")
unsubscribe_emby = on_command("取消订阅emby")
addemby = on_command("添加emby")
deleteemby = on_command("删除emby")

# Jellyfin 相关命令  
subscribe_jellyfin = on_command("订阅jellyfin")
unsubscribe_jellyfin = on_command("取消订阅jellyfin")
addjellyfin = on_command("添加jellyfin")
deletejellyfin = on_command("删除jellyfin")

@subscribe_emby.handle()
async def _(event: GroupMessageEvent):
    text = event.get_plaintext().strip()
    if text.startswith("订阅emby"):
        text = text[len("订阅emby"):].strip()
    args = text.split()
    if not args:
        await subscribe_emby.finish("用法：订阅emby 名称")
    name = args[0]
    group_id = event.group_id
    subscribe_dict = load_subscribe()
    server_info = subscribe_dict.get(name)
    if not server_info:
        await subscribe_emby.finish(f"Emby 名称 {name} 不存在。")
    if server_info.get("type") and server_info.get("type") != SERVER_TYPE_EMBY:
        await subscribe_emby.finish(f"{name} 不是 Emby 服务器。")
    if group_id in server_info.get("groups", []):
        await subscribe_emby.finish(f"本群已订阅 Emby({name}) 更新通知~")
    if "groups" not in server_info:
        server_info["groups"] = []
    server_info["groups"].append(group_id)
    save_subscribe(subscribe_dict)
    await subscribe_emby.finish(f"✅ 本群已成功订阅 Emby({name}) 更新！")

@unsubscribe_emby.handle()
async def _(event: GroupMessageEvent):
    text = event.get_plaintext().strip()
    if text.startswith("取消订阅emby"):
        text = text[len("取消订阅emby"):].strip()
    args = text.split()
    if not args:
        await unsubscribe_emby.finish("用法：取消订阅emby 名称")
    name = args[0]
    group_id = event.group_id
    subscribe_dict = load_subscribe()
    server_info = subscribe_dict.get(name)
    if not server_info:
        await unsubscribe_emby.finish(f"Emby 名称 {name} 不存在。")
    if server_info.get("type") and server_info.get("type") != SERVER_TYPE_EMBY:
        await unsubscribe_emby.finish(f"{name} 不是 Emby 服务器。")
    if group_id not in server_info.get("groups", []):
        await unsubscribe_emby.finish(f"本群尚未订阅 Emby({name}) 更新。")
    server_info["groups"].remove(group_id)
    save_subscribe(subscribe_dict)
    await unsubscribe_emby.finish(f"❎ 本群已取消 Emby({name}) 更新订阅。")

@addemby.handle()
async def _(event: GroupMessageEvent):
    text = event.get_plaintext().strip()
    if text.startswith("添加emby"):
        text = text[len("添加emby"):].strip()
    args = text.split()
    if len(args) < 2:
        await addemby.finish("用法：添加emby 名称 地址")
    name, url = args[0], args[1]
    subscribe_dict = load_subscribe()
    if name in subscribe_dict:
        await addemby.finish(f"名称 {name} 已存在。")
    subscribe_dict[name] = {"type": SERVER_TYPE_EMBY, "url": url, "groups": []}
    save_subscribe(subscribe_dict)
    await addemby.finish(f"✅ 已添加 Emby：{name}，地址：{url}")

@deleteemby.handle()
async def _(event: GroupMessageEvent):
    text = event.get_plaintext().strip()
    if text.startswith("删除emby"):
        text = text[len("删除emby"):].strip()
    args = text.split()
    if not args:
        await deleteemby.finish("用法：删除emby 名称")
    name = args[0]
    subscribe_dict = load_subscribe()
    if name not in subscribe_dict:
        await deleteemby.finish(f"Emby 名称 {name} 不存在。")
    if subscribe_dict.get(name, {}).get("type") and subscribe_dict[name].get("type") != SERVER_TYPE_EMBY:
        await deleteemby.finish(f"{name} 不是 Emby 服务器。")
    del subscribe_dict[name]
    save_subscribe(subscribe_dict)
    await deleteemby.finish(f"✅ 已删除 Emby：{name}")

# Jellyfin 命令处理
@subscribe_jellyfin.handle()
async def _(event: GroupMessageEvent):
    text = event.get_plaintext().strip()
    if text.startswith("订阅jellyfin"):
        text = text[len("订阅jellyfin"):].strip()
    args = text.split()
    if not args:
        await subscribe_jellyfin.finish("用法：订阅jellyfin 名称")
    name = args[0]
    group_id = event.group_id
    subscribe_dict = load_subscribe()
    server_info = subscribe_dict.get(name)
    if not server_info:
        await subscribe_jellyfin.finish(f"Jellyfin 名称 {name} 不存在。")
    if server_info.get("type") and server_info.get("type") != SERVER_TYPE_JELLYFIN:
        await subscribe_jellyfin.finish(f"{name} 不是 Jellyfin 服务器。")
    if group_id in server_info.get("groups", []):
        await subscribe_jellyfin.finish(f"本群已订阅 Jellyfin({name}) 更新通知~")
    if "groups" not in server_info:
        server_info["groups"] = []
    server_info["groups"].append(group_id)
    save_subscribe(subscribe_dict)
    await subscribe_jellyfin.finish(f"✅ 本群已成功订阅 Jellyfin({name}) 更新！")

@unsubscribe_jellyfin.handle()
async def _(event: GroupMessageEvent):
    text = event.get_plaintext().strip()
    if text.startswith("取消订阅jellyfin"):
        text = text[len("取消订阅jellyfin"):].strip()
    args = text.split()
    if not args:
        await unsubscribe_jellyfin.finish("用法：取消订阅jellyfin 名称")
    name = args[0]
    group_id = event.group_id
    subscribe_dict = load_subscribe()
    server_info = subscribe_dict.get(name)
    if not server_info:
        await unsubscribe_jellyfin.finish(f"Jellyfin 名称 {name} 不存在。")
    if server_info.get("type") and server_info.get("type") != SERVER_TYPE_JELLYFIN:
        await unsubscribe_jellyfin.finish(f"{name} 不是 Jellyfin 服务器。")
    if group_id not in server_info.get("groups", []):
        await unsubscribe_jellyfin.finish(f"本群尚未订阅 Jellyfin({name}) 更新。")
    server_info["groups"].remove(group_id)
    save_subscribe(subscribe_dict)
    await unsubscribe_jellyfin.finish(f"❎ 本群已取消 Jellyfin({name}) 更新订阅。")

@addjellyfin.handle()
async def _(event: GroupMessageEvent):
    text = event.get_plaintext().strip()
    if text.startswith("添加jellyfin"):
        text = text[len("添加jellyfin"):].strip()
    args = text.split()
    if len(args) < 2:
        await addjellyfin.finish("用法：添加jellyfin 名称 地址")
    name, url = args[0], args[1]
    subscribe_dict = load_subscribe()
    if name in subscribe_dict:
        await addjellyfin.finish(f"名称 {name} 已存在。")
    subscribe_dict[name] = {"type": SERVER_TYPE_JELLYFIN, "url": url, "groups": []}
    save_subscribe(subscribe_dict)
    await addjellyfin.finish(f"✅ 已添加 Jellyfin：{name}，地址：{url}")

@deletejellyfin.handle()
async def _(event: GroupMessageEvent):
    text = event.get_plaintext().strip()
    if text.startswith("删除jellyfin"):
        text = text[len("删除jellyfin"):].strip()
    args = text.split()
    if not args:
        await deletejellyfin.finish("用法：删除jellyfin 名称")
    name = args[0]
    subscribe_dict = load_subscribe()
    if name not in subscribe_dict:
        await deletejellyfin.finish(f"Jellyfin 名称 {name} 不存在。")
    if subscribe_dict.get(name, {}).get("type") and subscribe_dict[name].get("type") != SERVER_TYPE_JELLYFIN:
        await deletejellyfin.finish(f"{name} 不是 Jellyfin 服务器。")
    del subscribe_dict[name]
    save_subscribe(subscribe_dict)
    await deletejellyfin.finish(f"✅ 已删除 Jellyfin：{name}")
