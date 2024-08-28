# CreateNewExperimentLogTool

这个工具用于为某个成员在其实验日志数据库中新建实验记录。

注：这个工具是一个 `CollectAndAuthorizeTool` 模板工具，需要收集用户信息以及获取用户授权。

## 调用参数
- user_id (str): 成员名

## 工具描述
```text
This tool is used to create a new experiment log record for the user.
This tool is only used when the user asks for creating a new experiment log record,
or when other tools call this tool.

Args:
    user_id (str): The user_id of a lab member.

Returns:
    The tool's output and log.
```

详细内容参见 **源码文档** `Tools.memory.experiment.insert`