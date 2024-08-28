# 工具调用日志

## ToolLog
这个类记录某个工具调用的日志，包含如下信息：

- tool_name: 调用的工具名称
- log_to_user: 这部分日志将会作为额外信息加在Labridge对用户回复的末尾
- log_to_system: 这部分日志将存储于用户的交互日志数据库

具体细节请参考 **源码文档** `Tools.base.tool_log`