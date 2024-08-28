# Tool logs

## ToolLog
This class records the logs of a tool invocation, including the following information:

- tool_name: The name of the invoked tool
- log_to_user: This part of the log will be added as additional information at the end of Labridge’s response to the user.
- log_to_system: This part of the log will be stored in the user’s interaction log database.

Refer to **Code docs** `Tools.base.tool_log`