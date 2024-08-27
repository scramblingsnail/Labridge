import json
from pydantic import BaseModel
from pathlib import Path
from labridge.common.utils.time import get_time

from typing import List, Optional


READY_FOR_UPLOAD = "ReadyForUpload"
UPLOAD_SUCCESS = "UploadSuccess"
CLIENT_READY_FOR_DOWNLOAD = "ReadyForDownload"

USER_TMP_DIR = "tmp"


class BaseClientMessage(BaseModel):
	user_id: str
	reply_in_speech: bool


class FileWithTextMessage(BaseClientMessage):
	r"""
	This message includes:

	1. Basic: user_id
	2. The info of the file to be uploaded.
	3. The attached user's query.

	This message is used in the `websocket_chat_with_file`.
	"""
	file_name: str
	attached_text: str
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

	def set_file_path(self, f_path: str):
		if self.file_path is None:
			self.file_path = f_path


class ChatTextMessage(BaseClientMessage):
	r"""
	This message includes:

	1. Basic: user_id.
	2. The user's query.

	This message is used in the `websocket_chat_text`.
	"""
	text: str


class ChatSpeechMessage(BaseClientMessage):
	r"""
	This message includes:

	1. Basic: user_id.
	2. The save path of user's speech file data.

	This message is used in the `websocket_chat_speech`.
	"""
	speech_path: str


class PackedUserMessage:
	def __init__(
		self,
		user_id: str,
		system_msg: str,
		user_msg: str,
		reply_in_speech: bool
	):
		self.user_id = user_id
		self.system_msg = system_msg
		self.user_msg = user_msg
		self.reply_in_speech = reply_in_speech

	def dumps(self) -> str:
		msg_dict = {
			"user_id": self.user_id,
			"system_msg": self.system_msg,
			"user_msg": self.user_msg,
			"reply_in_speech": self.reply_in_speech,
		}
		return json.dumps(msg_dict)

	@classmethod
	def loads(cls, dumped_str: str):
		msg_dict = json.loads(dumped_str)
		return cls(
			user_id=msg_dict["user_id"],
			system_msg=msg_dict["system_msg"],
			user_msg=msg_dict["user_msg"],
			reply_in_speech=msg_dict["reply_in_speech"],
		)


class DownloadRequest(BaseClientMessage):
	file_path: str

	def dumps(self) -> str:
		msg_dict = {"file_path": self.file_path}
		return json.dumps(msg_dict)

	@classmethod
	def loads(cls, dumped_str: str):
		msg_dict = json.loads(dumped_str)
		return cls(
			user_id=msg_dict["user_id"],
			file_path=msg_dict["file_path"],
		)


class ServerDownloadMessage(BaseModel):
	r""" """
	file_name: str

	def dumps(self) -> str:
		msg_dict = {"file_name": self.file_name}
		return json.dumps(msg_dict)

	@classmethod
	def loads(cls, dumped_str: str):
		msg_dict = json.loads(dumped_str)
		return cls(
			file_name=msg_dict["file_name"]
		)


class ServerReply(BaseModel):
	reply_text: str
	references: Optional[List[str]] = None
	error: Optional[str] = None

	def dumps(self) -> str:
		msg_dict = {
			"reply_text": self.reply_text,
			"references": self.references,
			"error": self.error,
		}
		return json.dumps(msg_dict)

	@classmethod
	def loads(cls, dumped_str: str):
		msg_dict = json.loads(dumped_str)
		return cls(
			reply_text=msg_dict["reply_text"],
			references=msg_dict["references"],
			error=msg_dict["error"]
		)

class ServerSpeechReply(BaseModel):
	reply_speech_path: str



import time
import asyncio

from typing import Tuple, Dict, Union

from labridge.common.utils.asr.xunfei import ASRWorker
from labridge.common.utils.tts.xunfei import TTSWorker
from labridge.common.utils.time import get_time
from labridge.accounts.users import AccountManager
from common.utils.chat import pack_user_message
from pathlib import Path


class UserMsgFormatter(object):

	def _speech_to_text(self, msg: ChatSpeechMessage) -> str:
		text = ASRWorker.transform(speech_path=msg.speech_path)
		return text

	def _formatted_file_with_text(self, msg: FileWithTextMessage, file_idx: int) -> Tuple[str, str]:
		system_str = f"Path of File {file_idx}: {msg.file_path}"
		user_str = f"The user query about the File {file_idx}:\n{msg.attached_text}"
		return system_str, user_str

	def formatted_msgs(self, msgs: List[BaseClientMessage]) -> PackedUserMessage:
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
		packed_msg = PackedUserMessage(
			reply_in_speech=reply_in_speech,
			system_msg=system_msg,
			user_id=user_id,
			user_msg=user_msg,
		)
		return packed_msg


class ChatMsgBuffer(object):
	def __init__(self):
		self.account_manager = AccountManager()
		self.user_msg_buffer: Dict[str, List[BaseClientMessage]] = {}
		self.agent_reply_buffer: Dict[str, Union[ServerReply, ServerSpeechReply]] = {}
		self.user_msg_formatter = UserMsgFormatter()
		root = Path(__file__)
		for i in range(3):
			root = root.parent
		self._root = root

	def reset_buffer(self):
		users = self.account_manager.get_users()
		self.user_msg_buffer = {user: [] for user in users}
		self.agent_reply_buffer = {user: None for user in users}

	def clear_user_msg(self, user_id: str):
		self.user_msg_buffer[user_id] = []

	async def put_user_msg(self, user_msg: BaseClientMessage):
		if not isinstance(user_msg, (FileWithTextMessage, ChatTextMessage, ChatSpeechMessage)):
			raise ValueError(f"The Msg type {type(user_msg)} is not supported.")

		user_id = user_msg.user_id
		self.account_manager.check_valid_user(user_id=user_id)
		self.user_msg_buffer[user_id].append(user_msg)

	async def get_user_msg(self, user_id: str, timeout: int) -> PackedUserMessage:
		start_time = time.time()

		while True:
			await asyncio.sleep(1)
			msgs = self.user_msg_buffer[user_id]
			end_time = time.time()
			if len(msgs) > 0 or end_time > start_time + timeout:
				self.clear_user_msg(user_id=user_id)
				break

		packed_msgs = self.user_msg_formatter.formatted_msgs(msgs=msgs)
		return packed_msgs

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

	def get_agent_reply(self, user_id: str) -> Union[ServerReply, ServerSpeechReply]:
		agent_reply = self.agent_reply_buffer[user_id]
		if agent_reply is None:
			return ServerReply(
				reply_text="Please wait.",
				end=False,
			)
		else:
			return agent_reply


ChatBuffer = ChatMsgBuffer()
