# SetCurrentExperimentTool

这个工具用于为某个成员设置当前进行的实验，实验进行期间的日志将会添加在该实验的对应记录中。

注：这个工具是一个 `CollectAndAuthorizeTool` 模板工具，需要收集用户信息以及获取用户授权。

## 调用参数
- user_id (str): 成员名

## 工具描述
```text
This tool is used to record the experiment log of the experiment in progress for a user.

If the no experiment record exists or experiment in progress is not valid, this tool will call
the corresponding tools to help the user.

Args:
    user_id (str): The user_id of a lab member.
    log_str (str): The experiment log to be recorded.

Returns:
    The tool output and log.
```

详细内容参见 **源码文档** `Tools.memory.experiment.insert`