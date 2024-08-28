# Interaction log storage

## _"Reviewing the old and learning the new."_

In addition to serving the current conversation with [short-term memory](short-term_history.md), 
Labridge will keep interaction logs with each member of the lab. 
The contents of the interaction logs include:

### Chat logs
Recording the chat logs between members and Labridge in units of single **QA**.

### Tool invocation logs
If any tools are invoked by Labridge during the QA process, 
the relevant tool logs (ToolLog) will also be recorded in this QA record.
Refer to **Code docs** `tools.base.tool_log` for the data structure of `ToolLog`.

The above information will be recorded as a vector database, allowing Labridge to retrieve it at an appropriate time, 
providing Labridge with long-term memory functionality.

You can learn more about the [structure](long-term_history/store.md) 
and [retrieval](long-term_history/retrieve.md) of the interaction log vector database.
