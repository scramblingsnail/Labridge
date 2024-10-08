# 个人实验日志检索

实验日志与时间有关，因此Labridge根据实验日志的[存储结构](store.md)采用多级检索 + 时间戳过滤的检索方式

![个人实验日志检索](./images/experiment_log_retrieve.png)

## 第一步检索
在第一步检索中，Labridge根据Query向量与所有实验节点的实验描述之间的相似性，检索出最有可能的 `experiment_top_k` 个实验。
同时，Labridge在所有的日志类型的节点中，根据相似性检索出最相似的 `first_top_k` 日志节点，并获取它们对应的实验节点。

这些检索所得的实验节点将作为下一步检索的范围。

## 第二步检索
在第一步检索所得的实验节点范围内，Labridge在这些实验节点的日志节点中检索出 `second_top_k` 个日志节点，作为检索结果。

## 时间戳过滤
在第二步检索中，Labridge会根据输入的起止时间（如果提供了）进行时间戳过滤。最终检索出的实验日志内容将提供给 **LLM** 作为输入。

关于个人实验日志检索的具体细节参见 **源码文档** `Func_modules.memory.experiment.retrieve_log`