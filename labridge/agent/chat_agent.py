import asyncio
from llama_index.core.agent.react.formatter import ReActChatFormatter
from llama_index.core import Settings
from llama_index.core.tools.types import AsyncBaseTool
from llama_index.core.memory.chat_memory_buffer import ChatMemoryBuffer
from llama_index.core.chat_engine.types import AgentChatResponse
from llama_index.core.storage.chat_store.simple_chat_store import SimpleChatStore

from labridge.tools.paper.temporary_papers.paper_retriever import RecentPaperRetrieveTool
from labridge.tools.paper.temporary_papers.paper_summarize import RecentPaperSummarizeTool
from labridge.tools.paper.global_papers.retriever import SharedPaperRetrieverTool
from labridge.tools.paper.download.arxiv_download import ArXivSearchDownloadTool
from labridge.tools.memory.experiment.retrieve import ExperimentLogRetrieveTool
from labridge.tools.paper.temporary_papers.insert import AddNewRecentPaperTool
from labridge.tools.memory.chat.retrieve import ChatMemoryRetrieverTool
from labridge.agent.react.prompt import MY_REACT_CHAT_SYSTEM_HEADER
from labridge.agent.react.react import InstructReActAgent
from labridge.models.utils import get_models
from labridge.tools.memory.experiment.insert import (
	CreateNewExperimentLogTool,
	SetCurrentExperimentTool,
	RecordExperimentLogTool,
)

from labridge.tools.common.date_time import GetCurrentDateTimeTool, GetDateTimeFromNowTool
from labridge.interface.types import (
	FileWithTextMessage,
	ChatTextMessage,
	ChatSpeechMessage,
	BaseClientMessage,
	ServerReply,
	ServerSpeechReply,
)
from labridge.common.utils.chat import pack_user_message
from labridge.func_modules.memory.chat.short_memory import ShortMemoryManager

from typing import Optional, List, Union


class _ChatAgent:
	r"""
	This is the Chat agent following the ReAct framework, with access to multiple tools
	ranging papers, instruments and experiments.
	"""
	_chat_engine: Optional[InstructReActAgent] = None
	_short_memory_manager: Optional[ShortMemoryManager] = ShortMemoryManager()

	@property
	def chat_engine(self) -> InstructReActAgent:
		if self._chat_engine is None:
			self._chat_engine = self.get_chat_engine()
		return self._chat_engine

	@property
	def short_memory_manager(self):
		return self._short_memory_manager


	async def get_response(self, user_id: str, prompt: str) -> AgentChatResponse:
		r""" Get the response from the user, with chat history. """
		chat_history = self.short_memory_manager.load_memory(user_id=user_id)
		prompt = pack_user_message(
			user_id=user_id,
			message_str=prompt,
		)
		response = await self.chat_engine.achat(
			message=prompt,
			chat_history=chat_history,
		)
		chat_history = self.chat_engine.memory.get()
		self.short_memory_manager.save_memory(user_id=user_id, chat_history=chat_history)
		return response


	async def chat_text(self, user_message: ChatTextMessage) -> ServerReply:
		r""" Chat in text. """
		user_id = user_message.user_id

		prompt = pack_user_message(
			user_id=user_message.user_id,
			message_str=user_message.text,
		)
		response = await self.get_response(user_id=user_id, prompt=prompt)
		ref_paths = response.metadata["references"]
		if len(ref_paths) < 1:
			ref_paths = None

		reply = ServerReply(
			reply_text = response.response,
			references = ref_paths,
		)
		return reply

	async def chat_speech(self, user_message: ChatSpeechMessage) -> ServerSpeechReply:
		r""" Chat in speech. """
		user_id = user_message.user_id
		speech_path = user_message.speech_path
		# TODO: transform speech to text.

		text = ""
		prompt = pack_user_message(
			user_id=user_id,
			message_str=text,
		)
		response = await self.get_response(user_id=user_id, prompt=prompt)

		# TODO: transform text to speech
		speech_path = ""
		reply = ServerSpeechReply(
			reply_speech_path=speech_path,
		)
		return reply

	async def chat_with_file(self, user_message: FileWithTextMessage) -> ServerReply:
		r""" Chat in text attached with a file. """
		user_id = user_message.user_id
		file_path = user_message.file_path

		prompt = pack_user_message(
			user_id=user_id,
			message_str=user_message.attached_text,
		)

		prompt += (
			f"Attached file path: {file_path}",
		)

		response = await self.get_response(user_id=user_id, prompt=prompt)
		ref_paths = response.metadata["references"]
		if len(ref_paths) < 1:
			ref_paths = None

		reply = ServerReply(
			reply_text=response.response,
			references=ref_paths,
		)
		return reply

	async def chat(self, user_message: BaseClientMessage) -> Union[ServerReply, ServerSpeechReply]:
		if isinstance(user_message, ChatTextMessage):
			return await self.chat_text(user_message=user_message)
		elif isinstance(user_message, ChatSpeechMessage):
			return await self.chat_speech(user_message=user_message)
		elif isinstance(user_message, FileWithTextMessage):
			return await self.chat_with_file(user_message=user_message)
		else:
			raise ValueError(f"Invalid message type: {type(user_message)}")

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
			# GetCurrentDateTimeTool(),
			# GetDateTimeFromNowTool(),
		]


	def get_chat_engine(self) -> InstructReActAgent:
		llm, embed_model = get_models()
		Settings.embed_model = embed_model
		Settings.llm = llm
		tools = self.get_tools()

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


ChatAgent = _ChatAgent()
