### nonebot_plugin_emby_webhook
AI写的emby更新推送  
食用方式  

将 nonebot_plugin_emby_webhook 放置 src\plugins 下，  启动nonebot  
打开emby设置里的通知选项，添加一个通知，名称随意，网址填http://127.0.0.1:15434/emby/webhook  
其中 http://127.0.0.1:15434 为你的nonebot2运行的地址  
通知类型选 媒体库 新媒体已添加（订阅成功后可点击 发送测试通知 验证成功与否）  
添加指令为 添加emby 你的emby服务器名称（*注 是emby服务器名称不是创建的用户名称） 你的emby服务器地址 
删除指令为 删除emby 你的emby服务器名称
订阅指令为 订阅emby 你的emby服务器名称
退订指令为 取消订阅emby  你的emby服务器名称


<img width="516" height="676" alt="QQ20250806-212636" src="https://github.com/user-attachments/assets/7c1b1cce-de8e-445e-a40e-39361883c218" />
