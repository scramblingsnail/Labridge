# Interaction Log Retrieval

The characteristic of interaction log retrieval is its strong correlation with time. 
Therefore, Labridge uses a retrieval method that combines similarity search and timestamp filtering for interaction log retrieval.

![Interaction Log Retrieval](./images/chatlog_retrieve.png)

## Timestamp filtering
Each **QA** log node records the corresponding timestamp. 
Labridge filters the log nodes based on the input start and end times to narrow the search scope.

## Similarity retrieval
In the filtered and narrowed-down log nodes, retrieve the most similar relevant_top_k interaction logs 
based on the similarity between the Query’s embedding vector and the **QA** log vectors.

## Add context
Since the interactions between Labridge and the members are often continuous multi-round QA, 
context (i.e., the previous QA and the subsequent QA) is added to all retrieval results to 
ensure the completeness of the interaction logs.

## Reorder by time
The order of the interaction logs greatly affects the semantics of the conversation. 
Therefore, after adding context, the obtained QA log nodes are deduplicated and sorted to ensure the coherence of the interaction logs.

Refer to **Code docs** `Func_modules.memory.chat.retrieve`