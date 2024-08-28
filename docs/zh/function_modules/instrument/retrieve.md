# 仪器信息检索

Labridge使用多级检索的方式检索相关仪器信息

## 第一步检索
在第一步检索中，Labridge使用 **LLM** 对Query文本与各实验仪器之间的相关性（依据仪器描述）进行打分，筛选出最相关的 `instrument_top_k` 个仪器。

## 第二步检索：
将检索范围限定为第一步检索所得的仪器，在这些仪器的信息中进行相似性检索，得到与Query向量最相关的 `top_k` 条信息。
这些信息作为检索结果提供给 **LLM** 作为参考信息。

关于仪器信息检索的细节，请参考 **源码文档** `Func_modules.instrument.retrieve.instrument_retrieve`
