### nonebot_plugin_emby_webhook
AI写的emby和jellyfin更新推送  

## 支持的服务

- ✅ **Emby** - 完全支持
- ✅ **Jellyfin** - 新增支持（v2.0+）

## 安装使用

将 nonebot_plugin_emby_webhook 放置 src\plugins 下，启动nonebot

## Emby 配置

1. 打开emby设置里的通知选项
2. 添加一个通知，名称随意
3. 网址填 `http://127.0.0.1:15434/emby/webhook` （其中 http://127.0.0.1:15434 为你的nonebot2运行的地址）
4. 通知类型选 **媒体库 新媒体已添加** （订阅成功后可点击 发送测试通知 验证成功与否）
5. 使用机器人指令：
   - **添加emby** `服务器名称 服务器地址`（例：`添加emby MyEmby http://127.0.0.1:8096`，添加后本群自动订阅）
   - **订阅emby** `服务器名称`（让本群订阅一个已存在的服务器）
   - **修改emby订阅**（交互式：回复序号选择服务器，再输入新地址）
   - **删除emby订阅**（交互式：回复序号取消本群订阅，服务器配置保留）

## Jellyfin 配置

1. 打开Jellyfin管理后台，进入 **插件 → 目录**
2. 搜索并安装 **Webhook** 插件
3. 安装后在 **插件 → Webhook** 中配置：
   - 创建新的 **Add Generic Destination**
   - **URL** 填入 `http://127.0.0.1:15434/jellyfin/webhook` （替换为你的nonebot地址）
   - **Notification Types** 选择 **Library Item Added** 等事件
   - **Template** 填入以下内容：
     ```json
     {
       "ServerName": "{{ServerName}}",
       "Name": "{{Name}}",
       "ItemType": "{{ItemType}}",
       "SeriesName": "{{SeriesName}}",
       "SeasonNumber00": "{{SeasonNumber00}}",
       "EpisodeNumber00": "{{EpisodeNumber00}}",
       "RunTimeTicks": "{{RunTimeTicks}}",
       "Overview": "{{Overview}}",
       "ItemId": "{{ItemId}}"
     }
     ```
4. 使用机器人指令：
   - **添加jellyfin** `服务器名称 服务器地址`（例：`添加jellyfin MyJellyfin http://127.0.0.1:8096`）添加后本群自动订阅
   - **订阅jellyfin** `服务器名称`（让本群订阅一个已添加的服务器）
   - **修改jellyfin订阅**（交互式：回复序号选择服务器，再输入新地址）
   - **删除jellyfin订阅**（交互式：回复序号取消本群订阅，服务器配置保留）


## 特性

- 🔄 支持 Emby 和 Jellyfin 同时运行
- 🛡️ 自动去重（保留最近5条消息记录）
- 🖼️ 自动生成剧集海报（Emby/Jellyfin 都没有海报时用 Bangumi 封面兜底）
- ⭐ 自动带上 Bangumi 评分与评分人数（结果按「剧名 + 季号」缓存，取不到时退回第一季并标注）
- ⏱️ 显示视频时长
- 📝 显示剧集简介（保留原文分段，超过 1000 字时按句子截断并补省略号）
- 👥 支持多个订阅群组

> 评分匹配说明：分季播出的作品在 Bangumi 上是独立条目（例如「转生贵族凭鉴定技能扭转人生
> 第三季」是单独条目）。插件会用「剧名 第N季」搜索，并校验条目名里是否标了对应季号，确认
> 是当季条目才取分；只有当季条目时显示当季分数，例如 `⭐ Bangumi评分：5.3分（30人评分）`。
> 找不到对应季度条目时退回主条目（第一季）的分数并标注，例如
> `⭐ Bangumi评分：5.1分（2102人评分·第一季）`；若退回时干脆不想显示评分，把 `webhook.py`
> 里的 `BANGUMI_FALLBACK_TO_SERIES` 改为 `False`。剧场版/电影以及第一季按剧名直接匹配主条目。

## 数据格式说明

订阅信息保存在 `emby_subscribe.json`：

```json
{
  "MyEmby": {
    "type": "emby",
    "url": "http://127.0.0.1:8096",
    "groups": [123456789]
  },
  "MyJellyfin": {
    "type": "jellyfin",
    "url": "http://127.0.0.1:8096",
    "groups": [123456789]
  }
}
```
<img width="1415" height="847" alt="QQ_1778954443408" src="https://github.com/user-attachments/assets/e3f92639-39de-4b63-a9fc-6ed61fe0c8c8" />
