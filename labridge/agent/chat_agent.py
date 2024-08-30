import asyncio
from llama_index.core.agent.react.formatter import ReActChatFormatter
from llama_index.core import Settings
from llama_index.core.tools.types import AsyncBaseTool
from llama_index.core.memory.chat_memory_buffer import ChatMemoryBuffer
from llama_index.core.chat_engine.types import AgentChatResponse
from llama_index.core.storage.chat_store.simple_chat_store import SimpleChatStore

from labridge.tools.paper.temporary_papers.paper_retriever import RecentPaperRetrieveTool
from labridge.tools.paper.temporary_papers.paper_summarize import RecentPaperSummarizeTool
from labridge.tools.paper.shared_papers.retriever import SharedPaperRetrieverTool
from labridge.tools.paper.download.arxiv_download import ArXivSearchDownloadTool
from labridge.tools.memory.experiment.retrieve import ExperimentLogRetrieveTool
from labridge.tools.paper.temporary_papers.insert import AddNewRecentPaperTool
from labridge.tools.memory.chat.retrieve import ChatMemoryRetrieverTool
from labridge.tools.instrument.retrieve import InstrumentRetrieverTool
from labridge.agent.react.prompt import LABRIDGE_CHAT_SYSTEM_HEADER
from labridge.accounts.users import AccountManager
from labridge.agent.react.react import InstructReActAgent
from labridge.agent.chat_msg.msg_types import PackedUserMessage, AgentResponse
from labridge.models.utils import get_models
from labridge.tools.memory.experiment.insert import (
	CreateNewExperimentLogTool,
	SetCurrentExperimentTool,
	RecordExperimentLogTool,
)

from labridge.func_modules.memory.chat.short_memory import ShortMemoryManager


from typing import Optional, List, Union, Dict


class LabChatAgent:
	r"""
	This is the Chat agent following the ReAct framework, with access to multiple tools
	ranging papers, instruments and experiments.
	"""

	def __init__(
		self,
		chat_engine: InstructReActAgent = None,
	):
		self._chat_engine = chat_engine
		self._short_memory_manager = ShortMemoryManager()
		self._account_manager = AccountManager()
		self._chatting_status = {}
		self.reset_chatting_status()

	def reset_chatting_status(self):
		users = self._account_manager.get_users()
		self._chatting_status = {user: False for user in users}

	@property
	def chat_engine(self) -> InstructReActAgent:
		if self._chat_engine is None:
			self._chat_engine = self.get_chat_engine()
		return self._chat_engine


	def is_chatting(self, user_id: str) -> bool:
		return self._chatting_status[user_id]

	def set_chatting(self, user_id: str, chatting: bool):
		self._chatting_status[user_id] = chatting

	@property
	def short_memory_manager(self):
		return self._short_memory_manager

	async def chat(self, packed_msgs: PackedUserMessage) -> AgentResponse:
		r""" Chat with agent. """
		user_id = packed_msgs.user_id
		self.set_chatting(user_id=user_id, chatting=True)
		packed_json = packed_msgs.dumps()
		chat_history = self.short_memory_manager.load_memory(user_id=user_id)

		response = await self.chat_engine.achat(
			message=packed_json,
			chat_history=chat_history,
		)
		chat_history = self.chat_engine.memory.get()
		self.short_memory_manager.save_memory(user_id=user_id, chat_history=chat_history)

		ref_paths = response.metadata["references"]
		if len(ref_paths) < 1:
			ref_paths = None

		agent_response = AgentResponse(
			response=response.response,
			references=ref_paths,
		)
		return agent_response

	def test_chat(self, packed_msgs: PackedUserMessage) -> AgentResponse:
		r""" Debug. """
		user_id = packed_msgs.user_id
		self.set_chatting(user_id=user_id, chatting=True)
		packed_json = packed_msgs.dumps()
		chat_history = self.short_memory_manager.load_memory(user_id=user_id)

		response = self.chat_engine.chat(
			message=packed_json,
			chat_history=chat_history,
		)
		chat_history = self.chat_engine.memory.get()
		self.short_memory_manager.save_memory(user_id=user_id, chat_history=chat_history)

		ref_paths = response.metadata["references"]
		if len(ref_paths) < 1:
			ref_paths = None

		agent_response = AgentResponse(
			response=response.response,
			references=ref_paths,
		)
		return agent_response


	def get_tools(self) -> List[AsyncBaseTool]:
		r""" Available tools. """
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
			InstrumentRetrieverTool(),
		]

	def get_chat_engine(self) -> InstructReActAgent:
		llm, embed_model = get_models()
		Settings.embed_model = embed_model
		Settings.llm = llm
		tools = self.get_tools()

		react_chat_formatter = ReActChatFormatter.from_defaults(system_header=LABRIDGE_CHAT_SYSTEM_HEADER)

		chat_engine = InstructReActAgent.from_tools(
			tools=tools,
			react_chat_formatter=react_chat_formatter,
			verbose=False,
			llm=llm,
			memory=ChatMemoryBuffer.from_defaults(token_limit=3000),
			enable_instruct=False,
			enable_comment=False,
			max_iterations=20,
		)
		return chat_engine


ChatAgent = LabChatAgent()
