import json
import os
import time
import asyncio
import fsspec

from pydantic import BaseModel
from typing import Tuple, Dict, Union

from labridge.common.utils.asr.xunfei import ASRWorker
from labridge.common.utils.tts.xunfei import TTSWorker
from labridge.common.utils.time import get_time
from labridge.accounts.users import AccountManager
from pathlib import Path

from typing import List, Optional


READY_FOR_UPLOAD = "ReadyForUpload"
UPLOAD_SUCCESS = "UploadSuccess"
CLIENT_READY_FOR_DOWNLOAD = "ReadyForDownload"

USER_TMP_DIR = "tmp"

USER_SPEECH_NAME = "user_speech"
SUPPORT_USER_SPEECH_SUFFIX = [".wav"]

AGENT_SPEECH_NAME = "agent_reply"



class BaseClientMessage(BaseModel):
	r"""
	This is the base class for client's messages.

	user_id (str): The user id of a Lab member.
	reply_in_speech (bool): If True, the agent will reply in speech.
	enable_instruct (bool): If True, enable the user to intervene into the agent's reasoning phase.
	enable_comment (bool): If True: enable the user to intervene into the agent's acting phase.
	"""
	user_id: str
	reply_in_speech: bool
	enable_instruct: bool
	enable_comment: bool


class FileWithTextMessage(BaseClientMessage):
	r"""
	This message includes:

	1. Basic: user_id
	2. The info of the file to be uploaded.
	3. The attached user's query.
	4. Whether to reply in speech or not.

	This message is used in the `websocket_chat_with_file`.
	"""
	attached_text: str
	reply_in_speech: bool = False
	file_path: Optional[str] = None

	def dumps(self) -> str:
		r"""
		The formatted string that the client sends to the server for uploading request,
		including the file info and the attached text.
		"""
		msg_dict = {
			"user_id": self.user_id,
			"file_name": self.file_name,
			"attached_text": self.attached_text
		}
		return json.dumps(msg_dict)

	@classmethod
	def loads(cls, dumped_str):
		msg_dict = json.loads(dumped_str)
		user_id = msg_dict.get("user_id")
		file_name = msg_dict.get("file_name")
		attached_text = msg_dict.get("attached_text")
		return cls(
			user_id=user_id,
			file_name=file_name,
			attached_text=attached_text,
		)


class ChatTextMessage(BaseClientMessage):
	r"""
	This message includes:

	1. Basic: user_id.
	2. The user's query.

	This message is used in the `websocket_chat_text`.
	"""
	text: str
	reply_in_speech: bool = False


class ChatSpeechMessage(BaseClientMessage):
	r"""
	This message includes:

	1. Basic: user_id.
	2. The save path of user's speech file data.

	This message is used in the `websocket_chat_speech`.
	"""
	speech_path: str
	reply_in_speech: bool = True


class PackedUserMessage:
	r"""
	Pack the user messages.

	user_id (str): The user id of a Lab member.
	system_msg (str): The corresponding system message.
	user_msg (str): The packed user messages.
	reply_in_speech (bool): Whether the agent should reply in speech or not
	chat_group_id (Optional[str]): The ID of a chat group (If the messages are from a chat group). Defaults to None.
	"""
	def __init__(
		self,
		user_id: str,
		system_msg: str,
		user_msg: str,
		chat_group_id: Optional[str] = None,
	):
		self.user_id = user_id
		self.system_msg = system_msg
		self.user_msg = user_msg
		self.chat_group_id = chat_group_id

	def dumps(self) -> str:
		msg_dict = {
			"user_id": self.user_id,
			"system_msg": self.system_msg,
			"user_msg": self.user_msg,
			"chat_group_id": self.chat_group_id,
		}
		return json.dumps(msg_dict)

	@classmethod
	def loads(cls, dumped_str: str):
		r"""
		Load from a dumped JSON string.

		Args:
			dumped_str (str): The dumped JSON string.

		Returns:
			PackedUserMessage
		"""
		msg_dict = json.loads(dumped_str)
		return cls(
			user_id=msg_dict["user_id"],
			system_msg=msg_dict["system_msg"],
			user_msg=msg_dict["user_msg"],
			chat_group_id=msg_dict["chat_group_id"],
		)


class AgentResponse(BaseModel):
	r"""
	The response of chat agent.

	response (str): The response string.
	references (Optional[List[str]]): The paths of reference files.
	"""
	response: str
	references: Optional[List[str]]


class ServerReply(BaseModel):
	r"""
	The server's text reply.

	reply_text (str): The reply text.
	valid (bool): Whether this reply contains valid information.
	references (Optional[Dict[str, int]]): The paths of reference files and file size.
	error (Optional[str]): The error information. If no error, it is None.
	inner_chat (Optional[bool]): Whether the reply is produced inside the Chat Call.
		- If this reply is the final response of the agent, it is False.
		- If this reply is an internal response such as collecting information from the user or getting authorization,
		it is True. When `inner_chat` is True, the client should post the user's answer to corresponding URL with flag `Inner`.
	"""
	reply_text: str
	valid: bool
	references: Optional[Dict[str, int]] = None
	extra_info: Optional[str] = None
	error: Optional[str] = None
	inner_chat: Optional[bool] = False


class ServerSpeechReply(BaseModel):
	r"""
	The server's speech reply.

	reply_speech (Dict[str, int]): The path of the agent's speech file.
	valid (bool): Whether the reply contains valid information. When receiving an invalid reply,
		the client should continue to get the server's reply until get a valid reply.
	references (Optional[List[str]]): The paths of reference files.
	inner_chat (Optional[bool]): Whether the reply is produced inside the Chat Call.
		- If this reply is the final response of the agent, it is False.
		- If this reply is an internal response such as collecting information from the user or getting authorization,
		it is True. When `inner_chat` is True, the client should post the user's answer to corresponding URL with flag `Inner`.
	"""
	reply_speech: Dict[str, int]
	valid: bool
	references: Optional[List[str]] = None
	extra_info: Optional[str] = None
	error: Optional[str] = None
	inner_chat: Optional[bool] = False


class UserMsgFormatter(object):
	r"""
	This class transform the user's messages into specific formats and generate corresponding system messages.
	"""

	def _speech_to_text(self, msg: ChatSpeechMessage) -> str:
		r""" Speech message to text. """
		text = ASRWorker.transform(speech_path=msg.speech_path)
		return text

	def _formatted_file_with_text(self, msg: FileWithTextMessage, file_idx: int) -> Tuple[str, str]:
		r""" FileWithTextMessage to formatted text. """
		system_str = f"Path of File {file_idx}: {msg.file_path}"
		user_str = f"The user query about the File {file_idx}:\n{msg.attached_text}"
		return system_str, user_str

	def formatted_msgs(self, msgs: List[BaseClientMessage]) -> PackedUserMessage:
		r"""
		Turn into formatted text message.

		Args:
			msgs (List[BaseClientMessage]): The user's messages.

		Returns:
			PackedUserMessage: The packed user messages, and system message.

		"""
		file_idx = 1
		user_id = msgs[0].user_id
		reply_in_speech = msgs[0].reply_in_speech
		enable_instruct = msgs[0].enable_instruct
		enable_comment = msgs[0].enable_comment

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
				if user_str:
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
		packed_msg = PackedUserMessage(
			system_msg=system_msg,
			user_id=user_id,
			user_msg=user_msg,
		)
		return packed_msg


class ChatConfig:
	def __init__(
		self,
		enable_instruct: bool = False,
		enable_comment: bool = False,
		reply_in_speech: bool = False,
	):
		self.enable_instruct = enable_instruct
		self.enable_comment = enable_comment
		self.reply_in_speech = reply_in_speech

	def update(
		self,
		enable_instruct: bool = None,
		enable_comment: bool = None,
		reply_in_speech: bool = None,
	):
		if enable_instruct is not None:
			self.enable_instruct = enable_instruct
		if enable_comment is not None:
			self.enable_comment = enable_comment
		if reply_in_speech is not None:
			self.reply_in_speech = reply_in_speech


class ChatMsgBuffer(object):
	r"""
	This class includes buffers that manager the messages from users and the agent's corresponding reply.

	Before a chat, the user's messages will put into the `user_msg_buffer`.
	When the agent get a user's messages, these messages will be packed and used as input to Call `Chat()`.

	Additionally, During the execution of `Chat()`, the agent is able to get new messages from the buffer, such as
	when collecting information from the user in some tools.

	The response of the agent will be put into the `agent_reply_buffer`, similarly, the user may receive an 'inner'
	response from the buffer.

	Depending on the user's choice `reply_in_speech`, the agent's response will be sent back to the user directly or
	transformed to speech before that.
	"""
	def __init__(self):
		root = Path(__file__)
		for i in range(4):
			root = root.parent
		self._root = root
		self.account_manager = AccountManager()
		self.user_msg_buffer: Dict[str, List[BaseClientMessage]] = {}
		self.agent_reply_buffer: Dict[str, Optional[Union[ServerReply, ServerSpeechReply]]] = {}
		self.config_buffer: Dict[str, ChatConfig] = {}
		self.user_msg_formatter = UserMsgFormatter()
		self.reset_buffer()
		self._fs = fsspec.filesystem("file")

	def reset_buffer(self):
		r"""
		Reset the user_msg_buffer and agent_reply_buffer.

		Returns:
			None
		"""
		users = self.account_manager.get_users()
		self.user_msg_buffer = {user: [] for user in users}
		self.agent_reply_buffer = {user: None for user in users}
		self.config_buffer = {user: ChatConfig() for user in users}

	def update_buffer_for_new_users(self):
		r"""
		When new users are registered, update the buffer.

		Returns:
			None
		"""
		users = self.account_manager.get_users()
		new_user_msg_buffer = {user: [] for user in users if user not in self.user_msg_buffer.keys()}
		new_agent_reply_buffer = {user: None for user in users if user not in self.agent_reply_buffer.keys()}
		new_config_buffer = {user: ChatConfig() for user in users if user not in self.config_buffer.keys()}
		self.user_msg_buffer.update(new_user_msg_buffer)
		self.agent_reply_buffer.update(new_agent_reply_buffer)
		self.config_buffer.update(new_config_buffer)

	def clear_user_msg(self, user_id: str):
		r"""
		Clear a user's messages in the buffer.

		Args:
			user_id (str): The user id of a Lab member.
		"""
		self.user_msg_buffer[user_id] = []

	def put_user_msg(self, user_msg: BaseClientMessage):
		r"""
		Put a new user message into the buffer.

		Args:
			user_msg (BaseClientMessage): A new message from a user.
		"""
		if not isinstance(user_msg, (FileWithTextMessage, ChatTextMessage, ChatSpeechMessage)):
			raise ValueError(f"The Msg type {type(user_msg)} is not supported.")

		user_id = user_msg.user_id
		self.account_manager.check_valid_user(user_id=user_id)
		self.user_msg_buffer[user_id].append(user_msg)
		self.config_buffer[user_id].update(
			enable_instruct=user_msg.enable_instruct,
			enable_comment=user_msg.enable_comment,
			reply_in_speech=user_msg.reply_in_speech,
		)

	async def get_user_msg(self, user_id: str, timeout: int = 240) -> Optional[PackedUserMessage]:
		r"""
		Wait until a user's messages are put into the buffer, and get them.

		Args:
			user_id (str): The user id of a Lab member.
			timeout (int): If timeout, return None.

		Returns:
			Optional[PackedUserMessage]: The obtained packed user messages.
				If no user messages if put in until time is out, return None.
		"""
		start_time = time.time()

		while True:
			msgs = self.user_msg_buffer[user_id]
			end_time = time.time()
			if len(msgs) > 0 or end_time > start_time + timeout:
				self.clear_user_msg(user_id=user_id)
				break
			await asyncio.sleep(1)
		if len(msgs) > 0:
			packed_msgs = self.user_msg_formatter.formatted_msgs(msgs=msgs)
			return packed_msgs

		no_reply_msg = PackedUserMessage(
			user_id=user_id,
			user_msg="",
			system_msg=f"The user {user_id} does not reply, end this conversation.",
		)
		return no_reply_msg

	def test_get_user_text(
		self,
		user_id: str,
		enable_instruct: bool = False,
		enable_comment: bool = False,
	) -> PackedUserMessage:
		r""" For debug. """
		user_msg = input("User: ")

		text_msg = ChatTextMessage(
			user_id=user_id,
			text=user_msg,
			reply_in_speech=False,
			enable_instruct=enable_instruct,
			enable_comment=enable_comment,
		)
		packed_msgs = self.user_msg_formatter.formatted_msgs(msgs=[text_msg])
		return packed_msgs

	def default_user_speech_path(self, user_id: str, speech_suffix: str) -> str:
		r""" Default save path of a user's speech. """
		if speech_suffix not in SUPPORT_USER_SPEECH_SUFFIX:
			raise ValueError(
				f"The audio file type {speech_suffix} is not supported,"
				f"use one of {SUPPORT_USER_SPEECH_SUFFIX} instead."
			)
		user_speech_path = self._root / f"{USER_TMP_DIR}/{user_id}/{USER_SPEECH_NAME}{speech_suffix}"
		dir_pth = str(user_speech_path.parent)
		if not self._fs.exists(dir_pth):
			self._fs.mkdirs(dir_pth)
		return str(user_speech_path)

	def default_agent_speech_path(self, user_id: str) -> str:
		r""" Default save path of agent's speech. """
		agent_speech_path = self._root / f"{USER_TMP_DIR}/{user_id}/{AGENT_SPEECH_NAME}"
		dir_pth = str(agent_speech_path.parent)
		if not self._fs.exists(dir_pth):
			self._fs.mkdirs(dir_pth)
		return str(agent_speech_path)

	def default_tmp_file_path(self, user_id: str, file_name: str) -> str:
		r""" Default save path of the user's uploaded file. """
		date, _ = get_time()
		tmp_dir = self._root / f"{USER_TMP_DIR}/{user_id}/{date}"
		tmp_path = str(tmp_dir / file_name)
		return tmp_path

	def put_agent_reply(
		self,
		user_id: str,
		reply_str: str,
		references: List[str] = None,
		inner_chat: bool = False,
		extra_info: str = None,
	):
		r"""
		Put an agent's reply into the buffer.

		Args:
			user_id (str): The user id of a Lab member.
			reply_str (str): The agent's reply string.
			references (List[str]): The paths of reference files. Defaults to None.
			inner_chat (bool): Whether the reply happens inside a chat.
			extra_info (str): extra information generally with long texts.
		"""
		self.account_manager.check_valid_user(user_id=user_id)

		if references is not None:
			ref_dict = {}
			for ref_path in references:
				if not self._fs.exists(ref_path):
					continue

				ref_size = os.path.getsize(ref_path)
				ref_dict[ref_path] = ref_size
			if ref_dict:
				references = ref_dict
			else:
				references = None

		if not self.config_buffer[user_id].reply_in_speech:
			reply = ServerReply(
				reply_text=reply_str,
				references=references,
				valid=True,
				inner_chat=inner_chat,
				extra_info=extra_info,
			)
			self.agent_reply_buffer[user_id] = reply
			return

		speech_name = self.default_agent_speech_path(user_id=user_id)
		speech_path = TTSWorker.transform(text=reply_str, speech_name=speech_name)

		speech_size = os.path.getsize(speech_path)
		reply = ServerSpeechReply(
			reply_speech={
				speech_path: speech_size,
			},
			inner_chat=inner_chat,
			references=references,
			valid=True,
			extra_info=extra_info,
		)
		self.agent_reply_buffer[user_id] = reply

	def get_agent_reply(self, user_id: str) -> Union[ServerReply, ServerSpeechReply]:
		r"""
		Get the agent reply to a user from the buffer.

		Args:
			user_id (str): The user id of a Lab member.

		Returns:
			Union[ServerReply, ServerSpeechReply]: If an agent's reply exists, return a valid reply,
				otherwise, return an invalid reply.
		"""
		agent_reply = self.agent_reply_buffer[user_id]
		if agent_reply is None:
			return ServerReply(
				reply_text="Please wait.",
				valid=False,
			)
		else:
			self.agent_reply_buffer[user_id] = None
			return agent_reply


ChatBuffer = ChatMsgBuffer()
