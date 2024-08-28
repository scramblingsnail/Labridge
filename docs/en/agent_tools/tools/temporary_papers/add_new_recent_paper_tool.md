# AddNewRecentPaperTool

This tool is used to add literature to a member’s recent paper database.

## Parameters
- user_id (str): Member name
- paper_file_path (str): Path of a new paper

## Description
```text
This tool is used to add a new paper to a specific user's recent papers storage.

Args:
    user_id (str): The user_id of a lab member.
    paper_file_path (str): The file path of the paper to be added. Browse the chat context or tool logs
        to get the correct and valid file path.

Returns:
    FuncOutputWithLog: The output and log.
```

Refer to **Code docs** `Tools.paper.temporary_papers.insert`