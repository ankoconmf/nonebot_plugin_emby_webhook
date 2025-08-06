### nonebot_plugin_emby_webhook
emby更新推送  
食用方式  

将 nonebot_plugin_emby_webhook 放置 src\plugins 下，修改 webhook.py 中的第 37 行 为你的emby地址，默认为http://127.0.0.1:8096，启动nonebot  
打开emby设置里的通知选项，添加一个通知，名称随意，网址填http://127.0.0.1:15434/emby/webhook  
其中 http://127.0.0.1:15434 为你的nonebot2运行的端口  
通知类型选 媒体库 新媒体已添加（订阅成功后可点击 发送测试通知 验证成功与否）  
订阅指令为 订阅emby  
退订指令为 取消订阅emby  


<img width="516" height="676" alt="QQ20250806-212636" src="https://github.com/user-attachments/assets/7c1b1cce-de8e-445e-a40e-39361883c218" />
