# SetCurrentExperimentTool

This tool is used to set up the current experiment for a specific member, and the logs during the experiment will be 
added to the corresponding record of that experiment.

Note: This tool is a `CollectAndAuthorizeTool` template tool, which requires collecting user information 
and obtaining user authorization.

## Parameters
- user_id (str): Member name

## Description
```text
This tool is used to record the experiment log of the experiment in progress for a user.

If the no experiment record exists or experiment in progress is not valid, this tool will call
the corresponding tools to help the user.

Args:
    user_id (str): The user_id of a lab member.
    log_str (str): The experiment log to be recorded.

Returns:
    The tool output and log.
```

Refer to **Code docs** `Tools.memory.experiment.insert`