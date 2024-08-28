# 交互日志

## _“温故而知新”_

除了为当前会话服务的[short-term memory](short-term_history.md)之外，Labridge会保存与实验室每个成员间的交互日志，
交互日志的内容包括：

### 聊天记录
以单次 **QA** 为单元，记录下成员与Labridge之间的聊天记录。

### 工具调用日志
如果在QA的过程中，Labridge调用了某些工具(Tools)，相关工具的日志(ToolLog)同样会记录在本次QA的记录中。
关于 `ToolLog` 的数据结构参见 **源码文档** `tools.base.tool_log`。

以上信息将记录为向量数据库，供Labridge在合适的时机进行检索，为Labridge提供长期记忆的功能。

您可以进一步了解交互日志向量数据库的[结构](long-term_history/store.md)与[检索](long-term_history/retrieve.md)
