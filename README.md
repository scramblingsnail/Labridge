# Labridge

## 代码结构

```text
- docs                  # 原始文档库目录
    - papers                # 原始文献库目录
    
- labridge              # 源代码目录
    - custom_query_engine   # 自定义 query engine
        - paper                 # 文献相关的 query engine
    - interface             # 前端接口
        - web                   # Web UI
    - llm                   # 模型
        - models                # 定义、获取模型
    - parse                 # 原始文档提取
        - paper                 # 文献相关的读取
          - extractors              # 文献Meta信息提取
          - parsers                 # PDF文献内容提取
          - paper_reader            # PaperReader
    - prompt                # 各种方面的提示词
        - chat
        - parse
        - query_transform
        - store
        - synthesize
    - retrieve              # 检索相关
        - log                   # 日志检索相关
        - paper                 # 文献数据库检索相关
        - query_transform       # 问题重写
    - store                 # 数据库存储
        - log                   # 日志数据库
        - paper                 # 文献数据库
    - synthesizer           # LLM响应后续处理
        - paper                 # 文献相关
        
- storage               # 数据库存储目录
    - papers                # 文献数据库
    
- tests                 # 测试用例 & debug
    - interface
    - parse
    - query_engine
    - retrieve
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
       
