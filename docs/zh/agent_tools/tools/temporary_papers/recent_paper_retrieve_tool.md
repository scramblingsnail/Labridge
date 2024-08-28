# RecentPaperRetrieveTool

这个工具用于从某个成员的近期文献库中检索相关信息。

## 调用参数
- paper_info (str): 目标文献的相关信息，如标题，文件路径等
- item_to_be_retrieved (str): 待检索信息
- user_id (str): 成员名
- start_date (Optional[str]): 时间过滤的开始日期
- end_date (Optional[str]): 时间过滤的结束日期
- kwargs (Any): 用于提高 **LLM** 调用本工具的容错

## 工具描述
```text
This tool is used to retrieve in the recent papers storage of a specific user.
These information should be provided:
1. The paper information, such as title or save path.
2. The specific question that you want to obtain answer from the paper.
3. The user id.

Args:
    paper_info (str): This argument is necessary.
        It is the relevant information of the paper.
        For example, it can be the paper title, or its save path.
    item_to_be_retrieved (str): This argument is necessary.
        It denotes the specific question that you want to retrieve in a specific paper.
    user_id (str): This argument is necessary.
        The user_id of a lab member.
    start_date (str): This argument is optional. It denotes the start date in the format 'Year-Month-Day'.
        If both start_date and end_date are specified, only papers which are added to storage between the
        start_date and end_date will be retrieved.
    end_date: This argument is optional. It denotes the end date in the format 'Year-Month-Day'.
    **kwargs: Other keyword arguments will be ignored.

Returns:
    The retrieved results.
```

详细内容参见 **源码文档** `Tools.paper.temporary_papers.paper_retriever`