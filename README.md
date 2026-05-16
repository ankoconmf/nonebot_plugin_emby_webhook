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
   - **添加emby** `服务器名称 服务器地址`（例：`添加emby MyEmby http://127.0.0.1:8096`）
   - **订阅emby** `服务器名称` 
   - **取消订阅emby** `服务器名称`
   - **删除emby** `服务器名称`

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
   - **添加jellyfin** `服务器名称 服务器地址`（例：`添加jellyfin MyJellyfin http://127.0.0.1:8096`）
   - **订阅jellyfin** `服务器名称`
   - **取消订阅jellyfin** `服务器名称`
   - **删除jellyfin** `服务器名称`
5. （可选）点击 **Send Test Notification** 测试通知是否正常工作

## 特性

- 🔄 支持 Emby 和 Jellyfin 同时运行
- 🛡️ 自动去重（保留最近5条消息记录）
- 🖼️ 自动生成剧集海报
- ⏱️ 显示视频时长
- 📝 显示剧集简介
- 👥 支持多个订阅群组

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
