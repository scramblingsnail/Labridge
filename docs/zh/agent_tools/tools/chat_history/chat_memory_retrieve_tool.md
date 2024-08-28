# SharedPaperRetrieverTool

这个工具用于从实验室共享文献库中检索相关信息。

## 调用参数
- item_to_be_retrieved (str): 待检索信息
- memory_id (str): 成员名或成员小组名
- start_date (Optional[str]): 时间过滤的开始日期
- end_date (Optional[str]): 时间过滤的结束日期
- kwargs (Any): 提高 **LLM** 调用本工具的容错

## 工具描述
```text
This tool is used to retrieve relevant chat history in a certain chat history memory.
The memory_id of a chat history memory is the `user_id` of a specific user or the `chat_group_id` of a specific
chat group.

Additionally, you can provide the `start_date` and `end_state` to limit the retrieving range of date,
The end date can be the same as the start date, but should not be earlier than the start date.
If the start date or end_date is not provided, retrieving will be performed among the whole memory.

Args:
    item_to_be_retrieved (str): Things that you want to retrieve in the chat history memory.
    memory_id (str): The memory_id of a chat history memory. It is either a `user_id` or a `chat_group_id`.
    start_date (str): The START date of the retrieving date limit. Defaults to None.
        If given, it should be given in the following FORMAT: Year-Month-Day.
        For example, 2020-12-1 means the year 2020, the 12th month, the 1rst day.
    end_date (str): The END date of the retrieving date limit. Defaults to None.
        If given, It should be given in the following FORMAT: Year-Month-Day.
        For example, 2024-6-2 means the year 2024, the 6th month, the 2nd day.

Returns:
    Retrieved chat history.
```

详细内容参见 **源码文档** `Tools.memory.chat.retrieve`
