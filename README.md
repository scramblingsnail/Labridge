# Labridge

## 环境

`python>=3.10.8`
`CUDA>=11.8`
`node=v18.12.0`

[requirements](./requirements.txt)

## 使用模型

Re-ranker model:
`bge-reranker-large`

LLM:
`Qwen2-7B-Instruct`

Embedding model:
`bge-large-zh-v1.5`

以上模型放在路径 `/root/autodl-tmp` 下。

## Run Web

Start backend server:

```sh
export PYTHONPATH=.
fastapi dev labridge/interface/web/http_server.py
```

Start frontend devtool:

```sh
cd web-frontend
npm i
npm start
```

## 代码结构

```text
- docs                  # 原始文档库目录
    - papers                # 原始文献库目录
    - cfgs

- labridge              # 源代码目录
    - common                # 通用组件
        - chat                  # chat相关
        - prompt                # prompt
        - query_engine          # query engine
    - interface             # 前端接口
        - web                   # Web Backend Server
    - llm                   # 模型
        - models                # 定义、获取模型
    - paper                 # 文献相关
        - download              # 文献信息获取与下载
        - parse                 # PDF文献内容提取
        - prompt                # 相关Prompt
        - query_engine          # 相关 query engine
        - retrieve              # 文献数据检索
        - store                 # 文献数据存储
        - synthesizer           # LLM响应后续处理
- storage               # 数据库存储目录
    - papers                # 文献数据库
- tests                 # 测试用例 & debug
    - interface
    - paper
- web-frontend          # 前端app
```

## Docstring

### 示例一

```text
r"""
Read a PDF paper, and extract valid meta_data from it.

Args:
    llm (LLM: the used llm, if not provided, use the llm from `service_context`.
        Defaults to None.
    source_keyword_threshold (int): used in PaperSourceAnalyzer. refer to PaperSourceAnalyzer for details.
        Defaults to 10
    use_llm_for_source (bool): whether to use LLM in the source analyzer. Defaults to True.
    extract_metadata (bool): whether to use LLM to extract metadata for papers. Defaults to True.
    necessary_metadata (Dict[str, str]): Paper level metadata.
        The necessary metadata that must be extracted.
        It is a dictionary with k-v pairs like: {metadata_name: description}. The description
        is used to instruct the llm to extract the corresponding metadata.
        For example:

        - key: "Title"
        - value: "The title often appears as a single concise sentence at the head of a paper."
    optional_metadata (Dict[str, str]): Paper level metadata.
        The optional metadata that is not forced to extract from the paper.
        It is a dictionary with k-v pairs like: {metadata_name: description}.
    extract_retry_times: max retry times if not all necessary metadata is extracted.
    transformations: The transformations to apply to the documents,
        including chunking operation and chunk-level transformations.
    service_context (ServiceContext): the service context.
    recursive (bool): Whether to recursively search in subdirectories.
        False by default.
    exclude (List): glob of python file paths to exclude (Optional)
    exclude_hidden (bool): Whether to exclude hidden files (dotfiles).
    required_exts (Optional[List[str]]): List of required extensions.
        Default is None.
    num_files_limit (Optional[int]): Maximum number of files to read.
        Default is None.
    filename_as_id (bool): whether to use the filename as the document id. True by default.
        If set to True, the doc node will be named as `{file_path}_{content_type}`.
        The file_path is relative to root directory.
"""
```

### 示例二:

```text
r"""
Read a single pdf paper.

Args:
    file_path (Union[Path, str]): the path of pdf paper.
    show_progress (bool): show parsing progress.

Returns:
    Tuple[List[Document], List[Document]]:
        The ingested content docs and extra docs.

        - chunk_docs: the docs for retrieving, include information such as main text, methods.
        Might be None if nothing is parsed (auto_parse_paper fails.)
        - extra_docs: docs that involve supplementary information such as references.
        Might be None.
"""
```

## Retrieve:

### Papers

在针对文献的检索中，我们采用了混合与多级检索的策略。

1. 在第一步检索中，我们使用了文献数据库中的向量数据库`VectorIndex`与 Summary 数据库`DocumentSummaryIndex`同时进行检索。
   其中，`VectorIndex`的检索依据是文章内容（References 除外）每个 `text_chunk` 与 `query_str`的 embedding 向量之间的相似性。
   `DocumentSummaryIndex`的检索依据是每篇文章的 Summary（在构建过程中提取）与`query_str`的 embedding 向量之间的相似性。
   将这二者检索所得的 nodes 的 `doc_id` 取并集，并在此基础上进行下一步检索。
2. 在第二步检索中，我们利用 LLM 对第一步中获得的 Papers, 与 `query_str`进行相关性排序，选出相关性最强的几篇 Paper。
3. 在第三步检索中，在对第二步中获得的 Paper 基础上，用它们的 `text_chunk` 与`query_str`的 embedding 向量之间的相似性进行排序，
   最后最相关的几个 `text_chunk`。
4. （可选）将以上检索所得的 nodes 的 `prev_node`, `next_node`, 以及对应的文献的 `summary_node` 加入到检索结果中。
