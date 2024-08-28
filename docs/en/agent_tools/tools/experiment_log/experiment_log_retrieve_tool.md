# ExperimentLogRetrieveTool

This tool is used to retrieve relevant information from a member’s experiment log database.

## Parameters
- item_to_be_retrieved (str): Information to be retrieved
- memory_id (str): Member name
- start_date (Optional[str]): Start date of time filter
- end_date (Optional[str]): End date of time filter
- experiment_name (Optional[str]): Specify the experiment name, limit the retrieving scope
- kwargs (Any): Improve the fault tolerance of **LLM** when calling this tool

## Description
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

Refer to **Code docs** `Tools.memory.experiment.retrieve`