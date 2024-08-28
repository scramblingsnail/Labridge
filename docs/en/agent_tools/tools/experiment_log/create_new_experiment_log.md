# CreateNewExperimentLogTool

This tool is used to create a new experiment record in the experiment log database for a specific member.

Note: This tool is a `CollectAndAuthorizeTool` template tool, which requires collecting user information 
and obtaining user authorization.

## Parameters
- user_id (str): Member name

## Description
```text
This tool is used to create a new experiment log record for the user.
This tool is only used when the user asks for creating a new experiment log record,
or when other tools call this tool.

Args:
    user_id (str): The user_id of a lab member.

Returns:
    The tool's output and log.
```

Refer to **Code docs** `Tools.memory.experiment.insert`