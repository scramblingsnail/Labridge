# RecordExperimentLogTool

This tool is used to record experiment logs for a specific member.

## Parameters
- user_id (str): Member name
- log_str (str): Experimental log

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