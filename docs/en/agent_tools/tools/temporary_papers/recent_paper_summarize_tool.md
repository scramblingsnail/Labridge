# RecentPaperSummarizeTool

This tool is used to summarize a paper in the member's recent paper database or to add a new paper 
to the recent paper database and summarize it.

## Parameters
- user_id (str): Member name
- paper_file_path (str): The path of the paper to be summarized

## Description
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

Refer to **Code docs** `Tools.paper.temporary_papers.paper_summarize`