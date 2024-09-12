简体中文|[English](README_EN.md)

# Labridge

## _搭建科学实验室沟通合作的桥梁_ 

**Labridge**致力于利用大模型整合与管理科学实验室的知识财富，包括文献内容、实验记录、仪器信息等，
以促进研究者们之间的沟通合作，加速对于新人研究者的培养，为实验室搭建沟通合作的桥梁。

![Labridge](./docs/assets/images/home.jpg)

## 开发框架
Labridge基于 `Llamaindex` 与 `Mindspore`, 使用ReAct + CoT Prompt框架进行实现。

![Framework](./docs/zh/agent_tools/tools/images/react_tools.png)

## 用户界面
Labridge提供Web与App版的用户界面。

[Web](./docs/zh/interface/web_ui.md)

[App](./docs/zh/interface/app.md)


## 环境

`python==3.8`
`CUDA>=11.8`
`node=v18.12.0`

## Requirements (Mnidspore版本)
[requirements_mindspore](./requirements/requirements_mindspore.txt)

## Requirements (Pytorch版本)

[requirements](./requirements/requirements.txt)

## 项目文档
我们提供详细的中英文项目文档与源码文档，细节请参阅如下文档：

**中文文档**

[中文文档地址一](https://scramblingsnail.github.io/Labridge/)

[中文文档地址二](https://labridge.readthedocs.io/zh-cn/latest/)

**英文文档**

[英文文文档地址一](https://scramblingsnail.github.io/Labridge/en/)

[英文文文档地址二](https://labridge.readthedocs.io/zh-cn/latest/en/)
