# Agent可调用工具

Labridge目前可调用如下工具：

- [SharedPaperRetrieverTool](./shared_papers/shared_paper_retrieve_tool.md)
- [RecentPaperRetrieveTool](./temporary_papers/recent_paper_retrieve_tool.md)
- [RecentPaperSummarizeTool](./temporary_papers/recent_paper_summarize_tool.md)
- [ArXivSearchDownloadTool](./temporary_papers/arxiv_search_download_tool.md)
- [AddNewRecentPaperTool](./temporary_papers/add_new_recent_paper_tool.md)
- [ExperimentLogRetrieveTool](./experiment_log/experiment_log_retrieve_tool.md)
- [CreateNewExperimentLogTool](./experiment_log/create_new_experiment_log.md)
- [SetCurrentExperimentTool](./experiment_log/set_current_experiment_tool.md)
- [RecordExperimentLogTool](./experiment_log/record_experiment_log_tool.md)
- [ChatMemoryRetrieverTool](./chat_history/chat_memory_retrieve_tool.md)

所有需要实验室成员授权的操作被定义为 **CallbackOperation**, 
如创建实验记录、下载文献等。
**CallbackOperation** 的具体定义参见 **源码文档** `Callback.base.operation_base`

目前的 **CallbackOperation** 包括：

- **ArxivDownloadOperation**
参见 **源码文档** `Callback.paper.paper_download`
- **AddNewRecentPaperOperation**
参见 **源码文档** `Callback.paper.add_recent_paper`
- **PaperSummarizeOperation**
参见 **源码文档** `Callback.paper.paper_summarize`
- **CreateNewExperimentLogOperation**
参见 **源码文档** `Callback.experiment_log.new_experiment`
- **SetCurrentExperimentOperation**
参见 **源码文档** `Callback.experiment_log.set_current_experiment`


我们提供如下工具模板，用以开发符合 

“收集用户信息 --> 定义执行操作 --> 征取用户授权 --> 执行Callback操作” 

流程的工具

- [CollectAndAuthorizeTool](./interact/collect_and_authorize_tool.md)