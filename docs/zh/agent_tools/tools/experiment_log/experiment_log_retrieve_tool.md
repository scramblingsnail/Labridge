# ExperimentLogRetrieveTool

这个工具用于从某个成员的实验日志数据库中检索相关信息。

## 调用参数
- item_to_be_retrieved (str): 待检索信息
- memory_id (str): 成员名
- start_date (Optional[str]): 时间过滤的开始日期
- end_date (Optional[str]): 时间过滤的结束日期
- experiment_name (Optional[str]): 指定实验名称，限制检索范围
- kwargs (Any): 提高 **LLM** 调用本工具的容错

## 工具描述
```text
This tool is used to retrieve experiment logs of a user.
Use this tool to help you to answer questions about experimental records.

Args:
    item_to_be_retrieved (str): This argument is necessary.
        It denotes things that you want to retrieve in the chat history memory.
    memory_id (str): This argument is necessary.
        It is the user_id of a lab member.
    start_date (str): This argument is optional.
        It denotes the start date in the format 'Year-Month-Day'.
        If both start_date and end_date are specified, only logs which are recorded between the
        start_date and end_date will be retrieved.
    end_date (str): This argument is optional.
        It denotes the end date in the format 'Year-Month-Day'.
    experiment_name (str): This argument is optional.
        It is the name of a specific experiment.
        If it is specified and is valid, only logs of this experiment will be retrieved.
    kwargs: Other arguments will be ignored.

Returns:
    Retrieved experiment logs.
```

详细内容参见 **源码文档** `Tools.memory.experiment.retrieve`