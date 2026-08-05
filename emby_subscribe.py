from nonebot.plugin import on_command
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.params import ArgPlainText
from nonebot.typing import T_State
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
addemby = on_command("添加emby")

# Jellyfin 相关命令
subscribe_jellyfin = on_command("订阅jellyfin")
addjellyfin = on_command("添加jellyfin")

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
    # 添加时默认让本群订阅，省去再执行一次「订阅emby」
    subscribe_dict[name] = {
        "type": SERVER_TYPE_EMBY,
        "url": url.rstrip("/"),
        "groups": [event.group_id],
    }
    save_subscribe(subscribe_dict)
    await addemby.finish(
        f"✅ 已添加 Emby：{name}，地址：{url.rstrip('/')}\n"
        f"本群已自动订阅更新通知~"
    )

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
    # 添加时默认让本群订阅，省去再执行一次「订阅jellyfin」
    subscribe_dict[name] = {
        "type": SERVER_TYPE_JELLYFIN,
        "url": url.rstrip("/"),
        "groups": [event.group_id],
    }
    save_subscribe(subscribe_dict)
    await addjellyfin.finish(
        f"✅ 已添加 Jellyfin：{name}，地址：{url.rstrip('/')}\n"
        f"本群已自动订阅更新通知~"
    )


# ================= 交互式管理订阅 =================
# 超时取消由 nonebot 的 session_expire_timeout 处理（默认 2 分钟）

modify_emby_sub = on_command("修改emby订阅")
delete_emby_sub = on_command("删除emby订阅")
modify_jellyfin_sub = on_command("修改jellyfin订阅")
delete_jellyfin_sub = on_command("删除jellyfin订阅")


def match_type(server_info, server_type):
    """判断服务器类型是否匹配（旧配置无 type 字段时视为 Emby）"""
    info_type = server_info.get("type")
    if not info_type:
        return server_type == SERVER_TYPE_EMBY
    return info_type == server_type


def list_group_servers(group_id, server_type):
    """列出本群订阅的指定类型服务器名称"""
    subscribe_dict = load_subscribe()
    return [
        name
        for name, info in subscribe_dict.items()
        if match_type(info, server_type)
        and group_id in info.get("groups", [])
    ]


def build_server_menu(names, subscribe_dict, action):
    """生成带序号的服务器列表"""
    lines = [f"请回复序号选择要{action}的服务器："]
    for index, name in enumerate(names, start=1):
        url = subscribe_dict.get(name, {}).get("url", "")
        lines.append(f"{index}. {name}（{url}）")
    lines.append("回复「取消」可终止操作，2 分钟无回应自动取消。")
    return "\n".join(lines)


async def start_select(matcher, event, state, server_type, type_label, action):
    """第一步：展示本群订阅的服务器列表"""
    names = list_group_servers(event.group_id, server_type)
    if not names:
        await matcher.finish(f"本群还没有订阅任何 {type_label} 服务器。")

    subscribe_dict = load_subscribe()
    state["names"] = names
    state["type_label"] = type_label
    await matcher.send(build_server_menu(names, subscribe_dict, action))


def resolve_choice(state, text):
    """解析用户回复的序号，返回选中的服务器名称"""
    names = state["names"]
    if not text.isdigit():
        return None
    index = int(text)
    if index < 1 or index > len(names):
        return None
    return names[index - 1]


@modify_emby_sub.handle()
async def _(event: GroupMessageEvent, state: T_State):
    await start_select(
        modify_emby_sub, event, state,
        SERVER_TYPE_EMBY, "Emby", "修改",
    )


@modify_emby_sub.got("choice")
async def _(state: T_State, choice: str = ArgPlainText()):
    text = choice.strip()
    if text in ("取消", "cancel"):
        await modify_emby_sub.finish("已取消操作。")

    name = resolve_choice(state, text)
    if not name:
        await modify_emby_sub.reject("序号无效，请重新回复列表中的序号。")

    state["name"] = name


@modify_emby_sub.got("url", prompt="请输入新的 Emby 地址：")
async def _(state: T_State, url: str = ArgPlainText()):
    new_url = url.strip()
    if new_url in ("取消", "cancel"):
        await modify_emby_sub.finish("已取消操作。")
    if not new_url.startswith(("http://", "https://")):
        await modify_emby_sub.reject(
            "地址需以 http:// 或 https:// 开头，请重新输入。"
        )

    name = state["name"]
    subscribe_dict = load_subscribe()
    if name not in subscribe_dict:
        await modify_emby_sub.finish(f"服务器 {name} 已不存在，操作取消。")

    old_url = subscribe_dict[name].get("url", "")
    subscribe_dict[name]["url"] = new_url.rstrip("/")
    save_subscribe(subscribe_dict)
    await modify_emby_sub.finish(
        f"✅ 修改完成\n{name}：{old_url} → {new_url.rstrip('/')}"
    )


@delete_emby_sub.handle()
async def _(event: GroupMessageEvent, state: T_State):
    await start_select(
        delete_emby_sub, event, state,
        SERVER_TYPE_EMBY, "Emby", "取消订阅",
    )


@delete_emby_sub.got("choice")
async def _(event: GroupMessageEvent, state: T_State, choice: str = ArgPlainText()):
    text = choice.strip()
    if text in ("取消", "cancel"):
        await delete_emby_sub.finish("已取消操作。")

    name = resolve_choice(state, text)
    if not name:
        await delete_emby_sub.reject("序号无效，请重新回复列表中的序号。")

    subscribe_dict = load_subscribe()
    server_info = subscribe_dict.get(name)
    if not server_info:
        await delete_emby_sub.finish(f"服务器 {name} 已不存在，操作取消。")

    groups = server_info.get("groups", [])
    if event.group_id not in groups:
        await delete_emby_sub.finish(f"本群已不在 {name} 的订阅列表中。")

    # 只移除本群订阅，服务器配置保留（可能有其他群仍在订阅）
    groups.remove(event.group_id)
    save_subscribe(subscribe_dict)
    await delete_emby_sub.finish(
        f"✅ 删除完成，本群已取消 Emby({name}) 更新订阅。"
    )


@modify_jellyfin_sub.handle()
async def _(event: GroupMessageEvent, state: T_State):
    await start_select(
        modify_jellyfin_sub, event, state,
        SERVER_TYPE_JELLYFIN, "Jellyfin", "修改",
    )


@modify_jellyfin_sub.got("choice")
async def _(state: T_State, choice: str = ArgPlainText()):
    text = choice.strip()
    if text in ("取消", "cancel"):
        await modify_jellyfin_sub.finish("已取消操作。")

    name = resolve_choice(state, text)
    if not name:
        await modify_jellyfin_sub.reject("序号无效，请重新回复列表中的序号。")

    state["name"] = name


@modify_jellyfin_sub.got("url", prompt="请输入新的 Jellyfin 地址：")
async def _(state: T_State, url: str = ArgPlainText()):
    new_url = url.strip()
    if new_url in ("取消", "cancel"):
        await modify_jellyfin_sub.finish("已取消操作。")
    if not new_url.startswith(("http://", "https://")):
        await modify_jellyfin_sub.reject(
            "地址需以 http:// 或 https:// 开头，请重新输入。"
        )

    name = state["name"]
    subscribe_dict = load_subscribe()
    if name not in subscribe_dict:
        await modify_jellyfin_sub.finish(f"服务器 {name} 已不存在，操作取消。")

    old_url = subscribe_dict[name].get("url", "")
    subscribe_dict[name]["url"] = new_url.rstrip("/")
    save_subscribe(subscribe_dict)
    await modify_jellyfin_sub.finish(
        f"✅ 修改完成\n{name}：{old_url} → {new_url.rstrip('/')}"
    )


@delete_jellyfin_sub.handle()
async def _(event: GroupMessageEvent, state: T_State):
    await start_select(
        delete_jellyfin_sub, event, state,
        SERVER_TYPE_JELLYFIN, "Jellyfin", "取消订阅",
    )


@delete_jellyfin_sub.got("choice")
async def _(event: GroupMessageEvent, state: T_State, choice: str = ArgPlainText()):
    text = choice.strip()
    if text in ("取消", "cancel"):
        await delete_jellyfin_sub.finish("已取消操作。")

    name = resolve_choice(state, text)
    if not name:
        await delete_jellyfin_sub.reject("序号无效，请重新回复列表中的序号。")

    subscribe_dict = load_subscribe()
    server_info = subscribe_dict.get(name)
    if not server_info:
        await delete_jellyfin_sub.finish(f"服务器 {name} 已不存在，操作取消。")

    groups = server_info.get("groups", [])
    if event.group_id not in groups:
        await delete_jellyfin_sub.finish(f"本群已不在 {name} 的订阅列表中。")

    # 只移除本群订阅，服务器配置保留（可能有其他群仍在订阅）
    groups.remove(event.group_id)
    save_subscribe(subscribe_dict)
    await delete_jellyfin_sub.finish(
        f"✅ 删除完成，本群已取消 Jellyfin({name}) 更新订阅。"
    )
