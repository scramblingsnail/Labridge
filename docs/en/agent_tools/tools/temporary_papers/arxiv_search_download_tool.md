# ArXivSearchDownloadTool

This tool is used to retrieve and download literature from arXiv for a member.

Note: This is a tool that requires the user's authorization.

## Parameters
- user_id (str): Member name
- search_str (str): Information to be retrieved
- kwargs (Any): Improve the fault tolerance of **LLM** when calling this tool

## Description
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

Refer to **Code docs** `Tools.paper.download.arxiv_download`