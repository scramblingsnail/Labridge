[简体中文](README.md)|English

# Labridge

## _Construct the bridges of a science laboratory_ 

**Labridge** is committed to build a bridge for communication and collaboration among all scientific laboratories, 
enhancing the efficiency of researchers and catalyzing the birth of new knowledge.

![Labridge](./docs/assets/images/home.jpg)

## Frameworks
Labridge is based on `Llamaindex` and `Mindspore` framework, and the ReAct + CoT Prompt framework is used to
construct agents.

![Framework](./docs/en/agent_tools/tools/images/react_tools.png)

## Project documents
We provide elaborated project documents and code documents, refer to the documents below for details.

**ZH Docs**

[ZH doc website 1](https://scramblingsnail.github.io/Labridge/)

[ZH doc website 2](https://labridge.readthedocs.io/zh-cn/latest/)

**EN Docs**

[EN doc website 1](https://scramblingsnail.github.io/Labridge/en/)

[EN doc website 2](https://labridge.readthedocs.io/zh-cn/latest/en/)

## Environment

`python==3.8`
`CUDA>=11.8`
`node=v18.12.0`

## Requirements (Mnidspore version)
[requirements_mindspore](./requirements/requirements_mindspore.txt)

## Requirements (Pytorch version)
[requirements](./requirements/requirements.txt)

## Model configuration
Set model configuration in the [configuration file](./model_cfg.yaml), such as LLM model name, embedding model name, 
deep learning framework, etc.

## Server & Client

### Run server
- Method 1 -- run in terminal:
```shell
python run_server.py --host={Your server host} --port={Your server port}
```

- Method 2 -- execute the shell script:
```shell
cd scripts
export LABRIDGE_SERVER_HOST={Your server host}
export LABRIDGE_SERVER_PORT={Your server port}
bash run_server.sh
```

Note: The description above is not for deployment on OrangePi.
Deployment on OrangePi needs extra GPU servers and the HTTP between Orange Pi and the GPU server.
Orange Pi executes light-weight tasks such as Embedding model, OCR, etc. The GPU server executes the computation tasks of LLM.
Refer to [Remote LLM](./labridge/models/remote/remote_models.py) and [Remote LLM server](./labridge/models/remote/remote_server.py)
for details.

### Communication between the server and client
refer to [http description](./docs/en/interface/server-client.md) for details.

### Client interface
Labridge provides web-version and app-version clients, please set the corresponding server host and port in the client.

For details about Web client, refer to
[Web](./docs/en/interface/web_ui.md)

For details about App client, refer to
[App](./docs/en/interface/app.md)
