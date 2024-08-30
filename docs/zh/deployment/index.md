# 基于昇腾软硬件的项目部署

基于昇腾的软硬件生态，我们对Labridge的项目部署采用了多层次的部署。

## 昇腾AI芯片加速Labridge运行
我们采用搭载昇腾AI芯片的 OrangePi 进行Embedding模型的部署，其搭载的昇腾AI芯片具备 **20TOPS** (FP16) AI算力，
充分加速Labridge的信息检索，发挥数据本地部署的优势，保障数据安全。

同时，大语言模型 (LLM) 部署在GPU服务器，通过HTTP与Embedding模型进行通信。

## 昇思赋能Labridge
不论是Embedding模型还是LLM，都依赖于 **Mindspore** 深度学习框架与 **MindNLP** 自然语言处理套件实现，
赋予了Labridge灵魂与智能引擎。
