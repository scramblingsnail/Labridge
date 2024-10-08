# 共享文献库构建

共享文献库的原始文件存放在 `documents/papers`路径下。该文献仓库的一级子目录为实验室成员的`user_id`

Labridge基于[Parse](parse.md)获得的文献内容与信息构建充分翔实的共享文献库，以支持多种方式的检索。

## **共享文献向量数据库**：
Labridge为所有的共享文献构建向量数据库(VectorIndex)，并记录每篇文献的Metadata，以及该文献的所有者。
内容向量数据库的构建参见源码文档 `Func_modules.paper.store.shared_paper_store`

共享文献向量数据库的结构如下图所示。该数据库为树形结构，第一层子节点为不同的用户，每个用户节点下会依照原始文献库中的目录树构建相应的
目录节点。文献节点记录该文献原始文件的相对路径，以及额外的Metadata如`Abstract`, `Summary`, `Authors`, `Title` 等等。
最后的叶子节点为每篇文献内容的文本块，前后文本块之间会有一定交叠。

![共享文献库结构](../images/shared_papers_structure.png)

### **内容总结**：
Labridge会使用 **LLM** 对加入共享文献库的每一篇文献的`MainText`部分与`Methods`部分进行总结，并构建相应的Summary向量数据库(SummaryVectorIndex)。
对于`MainText`与`Methods`进行总结的侧重点不一样。对于`MainText`的总结侧重于文章的整体内容，主要创新点等；
对于`Methods`的总结侧重于文章使用的技术路径。

- 内容总结的具体细节参见 **源码文档** `Func_modules.paper.synthesizer.summarize`
- 与Summary向量数据库相关的细节参见 **源码文档** `Func_modules.paper.store.paper_store`
- `MainText`, `Methods`总结相关提示词参见 **源码** `func_modules.paper.prompt.synthesize.paper_summarize`

### **文献目录总结**：
Labridge使用 **LLM** 递归地为文献仓库的每一级目录生成该目录的文献简介，如每个目录下文献涉及的研究领域等。
这些信息会作为Labridge为实验室成员推荐文献以及向共享文献库插入新文献的重要参考。
文献目录总结的具体细节参见 **源码文档** `Func_modules.paper.store.paper_store`

## **共享文献笔记向量数据库**
共享文献笔记向量数据库的结构如下图所示。该数据库是一个较为扁平化的树形结构，第一层节点为文献的DOI，对应一份独一无二的文献，其子节点为
不交叠的内容文本块，且文本块长度较短，以提供精细化的检索。每个文本块节点的子节点为笔记节点，记录该文本块中用户记录的笔记内容。

![共享文献笔记库结构](../images/shared_papers_note.png)
