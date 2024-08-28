# ArXivSearchDownloadTool

这个工具用于为某个成员从arXiv上检索并下载文献。

注：这是一个需要用户授权的工具。

## 调用参数
- user_id (str): 成员名
- search_str (str): 待检索信息
- kwargs (Any): 用于提高 **LLM** 调用本工具的容错

## 工具描述
```text
This tool is used to search relevant papers in arXiv and download the papers that the user is interested in.
When using the tool, be sure that the search_str MUST be English.
If the user do not use English, translate the search string to English first.

Args:
    user_id (str): The user_id of a lab member.
    search_str (str): The string that is used to search in arXiv.

Returns:
    FuncOutputWithLog: the operation output and log.
```

详细内容参见 **源码文档** `Tools.paper.download.arxiv_download`