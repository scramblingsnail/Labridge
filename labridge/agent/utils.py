import asyncio
from llama_index.core.agent.react.formatter import ReActChatFormatter
from llama_index.core.memory.chat_memory_buffer import ChatMemoryBuffer
from llama_index.core import Settings

from labridge.common.chat.chat import MY_REACT_CHAT_SYSTEM_HEADER
from labridge.llm.models import get_models
from labridge.common.chat.react import InstructReActAgent
from labridge.tools.memory.chat.retrieve import ChatMemoryRetrieverTool
from labridge.tools.memory.experiment.retrieve import ExperimentLogRetrieveTool
from labridge.tools.memory.experiment.insert import (
	CreateNewExperimentLogTool,
	SetCurrentExperimentTool,
	RecordExperimentLogTool,
)

from labridge.tools.paper.global_papers.retriever import SharedPaperRetrieverTool
from labridge.tools.paper.download.arxiv_download import ArXivSearchDownloadTool
from labridge.tools.paper.temporary_papers.insert import AddNewRecentPaperTool
from labridge.tools.paper.temporary_papers.paper_retriever import RecentPaperRetrieveTool
from labridge.tools.paper.temporary_papers.paper_summarize import RecentPaperSummarizeTool


from labridge.tools.common.date_time import GetCurrentDateTimeTool, GetDateTimeFromNowTool


def get_tools():
	return [
		ChatMemoryRetrieverTool(),
		ExperimentLogRetrieveTool(),
		CreateNewExperimentLogTool(),
		SetCurrentExperimentTool(),
		RecordExperimentLogTool(),
		SharedPaperRetrieverTool(),
		ArXivSearchDownloadTool(),
		AddNewRecentPaperTool(),
		RecentPaperRetrieveTool(),
		RecentPaperSummarizeTool(),
		GetCurrentDateTimeTool(),
		GetDateTimeFromNowTool(),
	]



def get_chat_engine():
	llm, embed_model = get_models()
	Settings.embed_model = embed_model
	Settings.llm = llm
	tools = get_tools()

	react_chat_formatter = ReActChatFormatter.from_defaults(system_header=MY_REACT_CHAT_SYSTEM_HEADER)

	chat_engine = InstructReActAgent.from_tools(
		tools=tools,
		react_chat_formatter=react_chat_formatter,
		verbose=True,
		llm=llm,
		memory=ChatMemoryBuffer.from_defaults(token_limit=3000),
		enable_instruct=False,
		enable_comment=False,
		max_iterations=20,
	)
	return chat_engine
