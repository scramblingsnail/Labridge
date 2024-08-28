# Tools callable by the agent.

Labridge can currently call the following tools:

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

All operations requiring authorization from lab members are defined as **CallbackOperation**
Such as creating experiment records, downloading papers, etc.
Refer to **Code docs** `Callback.base.operation_base` for details of **CallbackOperation**

The current CallbackOperation includes：

- **ArxivDownloadOperation**
Refer to **Code docs** `Callback.paper.paper_download`
- **AddNewRecentPaperOperation**
Refer to **Code docs** `Callback.paper.add_recent_paper`
- **PaperSummarizeOperation**
Refer to **Code docs** `Callback.paper.paper_summarize`
- **CreateNewExperimentLogOperation**
Refer to **Code docs** `Callback.experiment_log.new_experiment`
- **SetCurrentExperimentOperation**
Refer to **Code docs** `Callback.experiment_log.set_current_experiment`


We provide the following tool template for developing tools that comply with the process of 
"collecting user information --> defining execution operations --> obtaining user authorization --> executing Callback operations"

- [CollectAndAuthorizeTool](./interact/collect_and_authorize_tool.md)