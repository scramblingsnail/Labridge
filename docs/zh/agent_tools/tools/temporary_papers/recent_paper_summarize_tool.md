# RecentPaperSummarizeTool

这个工具用于为某个成员总结其近期文献库的文献，或将新文献加入近期文献库并总结。

## 调用参数
- user_id (str): 成员名
- paper_file_path (str): 待总结文献路径

## 工具描述
```text
This tool is used to summarize a paper that is stored in a specific user's recent papers storage.
This tool is used ONLY when the user explicitly ask for a summarization of the paper.
DO NOT use this tool by yourself.

Args:
    user_id (str): The user_id of a lab member.
    paper_file_path (str): The file path of a specific paper. Browse the chat context to get the correct
        and valid file path of the paper.

Returns:
    The summary of the paper.
```

详细内容参见 **源码文档** `Tools.paper.temporary_papers.paper_summarize`