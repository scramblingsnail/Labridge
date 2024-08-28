# Storage structure of personal experimental logs

Experiment logs are stored in a vector database.

- There is a root node in the database, and all experiment nodes are the children of this root node.
- Each experiment node includes the following information:

  - Experiment name
  - Experiment description
  - Relevant instruments
  - The creation time
- For each experiment, the experiment logs are recorded as child nodes of the experiment node, 
with the log nodes forming a structure similar to a doubly linked list in chronological order.
- the log nodes include the following information:

  - Experimental log
  - Record time

When laboratory members request Labridge to help record experimental results, Labridge will record the 
experimental results in the corresponding experiment log entry within his/her experiment log database.

For more details about the storage structure of personal experimental logs, 
refer to **Code docs** `Func_modules.memory.experiment.experiment_log`