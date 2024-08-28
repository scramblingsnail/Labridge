# RecentPaperRetrieveTool

This tool is used to retrieve relevant information from a member’s recent paper database.

## Parameters
- paper_info (str): Relevant information of the target paper, such as title, file path, etc.
- item_to_be_retrieved (str): Information to be retrieved
- user_id (str): Member name
- start_date (Optional[str]): Start date of time filter
- end_date (Optional[str]): End date of time filter
- kwargs (Any): Improve the fault tolerance of **LLM** when calling this tool

## Description
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

Refer to **Code docs** `Tools.paper.temporary_papers.paper_retriever`