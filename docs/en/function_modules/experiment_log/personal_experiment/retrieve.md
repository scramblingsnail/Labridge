# Personal experiment log retrieval

The experiment log is related to time, therefore, Labridge adopts a multi-level retrieval + timestamp filtering method 
based on the [storage structure](store.md) of the experiment log.

## The first retrieval step
In the first retrieval step, Labridge retrieves the most likely `experiment_top_k` experiments 
based on the similarity between the Query vector and the descriptions of all experiment nodes. 
At the same time, Labridge searches within all nodes of log types to retrieve the most similar 
`first_top_k` log nodes based on similarity, and obtains the corresponding experiment nodes for them.

The retrieved experiment nodes will serve as the scope for the next retrieval step.

## The second retrieval step
Within the range of experiment nodes obtained from the first retrieval step, Labridge retrieves `second_top_k` log nodes 
from the log nodes of these experiment nodes to serve as the retrieval results.

## Timestamp filtering
In the second retrieval step, Labridge will perform timestamp filtering based on the input start and end times (if provided). 
The ultimately retrieved experiment log content will be provided to **LLM** as input.

Refer to **Code docs** `Func_modules.memory.experiment.retrieve_log` for details of retrieval