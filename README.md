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
       
