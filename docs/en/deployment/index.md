# Deployment based on Ascend hardware and software


We deploy the Labridge project in a multi-level method based on Ascend hardware and software.

![Deployment based on Ascend hardware and software](./images/deployment.png)

## Accelerate the inference of Labridge by Ascend AI chip

We deploy the embedding model using OrangePi equipped with **Ascend** AI chips. 

The **Ascend** AI chip provides 20TOPS (FP16) AI computing power, 

significantly accelerating Labridge’s information retrieval, 

leveraging the advantages of local data deployment, and ensuring data security.


Meanwhile, the large language model (LLM) is deployed on a GPU server and communicates with the embedding model via HTTP.


## endow Labridge with its soul through Mindspore 


Both the embedding model and the LLM rely on the **Mindspore** deep learning framework and the **MindNLP** natural language processing suite, 

which endow Labridge with its soul and intelligent engine
