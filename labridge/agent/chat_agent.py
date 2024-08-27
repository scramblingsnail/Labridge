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
from labridge.agent.react.prompt import MY_REACT_CHAT_SYSTEM_HEADER
from labridge.accounts.users import AccountManager
from labridge.agent.react.react import InstructReActAgent
from labridge.models.utils import get_models
from labridge.tools.memory.experiment.insert import (
	CreateNewExperimentLogTool,
	SetCurrentExperimentTool,
	RecordExperimentLogTool,
)

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

from typing import Optional, List, Union, Dict


class LabChatAgent:
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


from labridge.agent.chat_agent.msg_types import (
	BaseClientMessage,
	FileWithTextMessage,
	ChatTextMessage,
	ChatSpeechMessage,
)

import time

from typing import Tuple

from labridge.common.utils.asr.xunfei import ASRWorker
from labridge.common.utils.tts.xunfei import TTSWorker
from labridge.common.utils.time import get_time
from labridge.agent.chat_agent.msg_types import USER_TMP_DIR
from common.utils.chat import pack_user_message
from pathlib import Path


class UserMsgFormatter(object):
	def __init__(self):
		self.a = 1

	def _speech_to_text(self, msg: ChatSpeechMessage) -> str:
		text = ASRWorker.transform(speech_path=msg.speech_path)
		return text

	def _formatted_file_with_text(self, msg: FileWithTextMessage, file_idx: int) -> Tuple[str, str]:
		system_str = f"Path of File {file_idx}: {msg.file_path}"
		user_str = f"The user query about the File {file_idx}:\n{msg.attached_text}"
		return system_str, user_str

	def formatted_msgs(self, msgs: List[BaseClientMessage]) -> str:
		file_idx = 1
		user_id = msgs[0].user_id
		reply_in_speech = msgs[0].reply_in_speech

		date_str, time_str = get_time()
		user_queries = []
		system_strings = [
			f"You are chatting with a user one-to-one\n"
			f"User id: {user_id}\n"
			f"Current date: {date_str}\n"
			f"Current time: {time_str}\n",
		]

		for msg in msgs:
			if isinstance(msg, ChatSpeechMessage):
				user_str = self._speech_to_text(msg=msg)
				user_queries.append(user_str)
			elif isinstance(msg, FileWithTextMessage):
				system_str, user_str = self._formatted_file_with_text(msg=msg, file_idx=file_idx)
				file_idx += 1
				user_queries.append(user_str)
				system_strings.append(system_str)
			elif isinstance(msg, ChatTextMessage):
				user_queries.append(msg.text)
			else:
				raise ValueError(f"Invalid Msg type: {type(msg)}")

		system_msg = "\n".join(system_strings)
		user_msg = "\n".join(user_queries)
		dumped_msgs = pack_user_message(user_id=user_id, system_msg=system_msg, user_msg=user_msg)
		return dumped_msgs


class ChatMsgBuffer(object):
	def __init__(self):
		self.account_manager = AccountManager()
		self.user_msg_buffer: Dict[str, List[BaseClientMessage]] = {}
		self.agent_reply_buffer: Dict[str, Union[ServerReply, ServerSpeechReply]] = {}
		root = Path(__file__)
		for i in range(4):
			root = root.parent
		self._root = root

	def reset_buffer(self):
		users = self.account_manager.get_users()
		self.user_msg_buffer = {user: [] for user in users}
		self.agent_reply_buffer = {user: None for user in users}

	def clear_user_msg(self, user_id: str):
		self.user_msg_buffer[user_id] = []

	def put_user_msg(self, user_msg: BaseClientMessage):
		if not isinstance(user_msg, (FileWithTextMessage, ChatTextMessage, ChatSpeechMessage)):
			raise ValueError(f"The Msg type {type(user_msg)} is not supported.")

		user_id = user_msg.user_id
		self.account_manager.check_valid_user(user_id=user_id)
		self.user_msg_buffer[user_id].append(user_msg)

	async def get_user_msg(self, user_id: str, timeout: int) -> List[BaseClientMessage]:
		start_time = time.time()

		while True:
			await asyncio.sleep(1)
			msgs = self.user_msg_buffer[user_id]
			end_time = time.time()
			if len(msgs) > 0 or end_time > start_time + timeout:
				break

		# TODO formatted msg.

		return msgs

	def put_agent_reply(
		self,
		user_id: str,
		reply_str: str,
		references: List[str],
		reply_in_speech: bool = False,
	):
		self.account_manager.check_valid_user(user_id=user_id)
		if not reply_in_speech:
			reply = ServerReply(
				reply_text=reply_str,
				references=references,
				end=True,
			)
			self.agent_reply_buffer[user_id] = reply
			return

		speech_path = self._root / f"{USER_TMP_DIR}/{user_id}/agent_reply.pcm"
		TTSWorker.transform(text=reply_str, speech_path=speech_path)
		reply = ServerSpeechReply(
			speech_path = speech_path,
			references=references,
			end=True,
		)
		self.agent_reply_buffer[user_id] = reply

	async def get_agent_reply(self, user_id: str) -> Union[ServerReply, ServerSpeechReply]:
		agent_reply = self.agent_reply_buffer[user_id]
		if agent_reply is None:
			return ServerReply(
				reply_text="Please wait.",
				end=False,
			)
		else:
			return agent_reply









ChatAgent = LabChatAgent()
