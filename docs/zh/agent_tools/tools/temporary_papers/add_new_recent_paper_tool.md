# AddNewRecentPaperTool

这个工具用于向某个成员的近期文献库中添加文献。

## 调用参数
- user_id (str): 成员信息
- paper_file_path (str): 新文献的路径

## 工具描述
```text
This tool is used to add a new paper to a specific user's recent papers storage.

Args:
    user_id (str): The user_id of a lab member.
    paper_file_path (str): The file path of the paper to be added. Browse the chat context or tool logs
        to get the correct and valid file path.

Returns:
    FuncOutputWithLog: The output and log.
```

详细内容参见 **源码文档** `Tools.paper.temporary_papers.insert`