import json
from pydantic import BaseModel
from pathlib import Path
from labridge.common.utils.time import get_time

import time
import asyncio

from typing import Tuple, Dict, Union

from labridge.common.utils.asr.xunfei import ASRWorker
from labridge.common.utils.tts.xunfei import TTSWorker
from labridge.common.utils.time import get_time
from labridge.accounts.users import AccountManager
from common.utils.chat import pack_user_message
from pathlib import Path

from typing import List, Optional


READY_FOR_UPLOAD = "ReadyForUpload"
UPLOAD_SUCCESS = "UploadSuccess"
CLIENT_READY_FOR_DOWNLOAD = "ReadyForDownload"

USER_TMP_DIR = "tmp"

USER_SPEECH_NAME = "user_speech.pcm"
AGENT_SPEECH_NAME = "agent_reply.pcm"




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
	def __init__(
		self,
		user_id: str,
		system_msg: str,
		user_msg: str,
		reply_in_speech: bool,
		chat_group_id: Optional[str] = None,
	):
		self.user_id = user_id
		self.system_msg = system_msg
		self.user_msg = user_msg
		self.reply_in_speech = reply_in_speech
		self.chat_group_id = chat_group_id

	def dumps(self) -> str:
		msg_dict = {
			"user_id": self.user_id,
			"system_msg": self.system_msg,
			"user_msg": self.user_msg,
			"reply_in_speech": self.reply_in_speech,
			"chat_group_id": self.chat_group_id,
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
			chat_group_id=msg_dict["chat_group_id"],
		)


class AgentResponse(BaseModel):
	response: str
	references: Optional[List[str]]
	reply_in_speech: bool



class ServerReply(BaseModel):
	reply_text: str
	valid: bool
	references: Optional[List[str]] = None
	error: Optional[str] = None
	inner_chat: Optional[bool] = False

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
	valid: bool
	reply_speech_path: str
	references: Optional[List[str]] = None
	inner_chat: Optional[bool] = False


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
		self.agent_reply_buffer: Dict[str, Optional[Union[ServerReply, ServerSpeechReply]]] = {}
		self.user_msg_formatter = UserMsgFormatter()
		self.reset_buffer()
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

	async def get_user_msg(self, user_id: str, timeout: int = 30) -> Optional[PackedUserMessage]:
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
		return None

	def test_get_user_text(self, user_id: str) -> PackedUserMessage:
		user_msg = input("User: ")

		text_msg = ChatTextMessage(
			user_id=user_id,
			text=user_msg,
			reply_in_speech=False,
		)
		packed_msgs = self.user_msg_formatter.formatted_msgs(msgs=[text_msg])
		return packed_msgs

	def default_user_speech_path(self, user_id: str) -> str:
		return str(self._root / f"{USER_TMP_DIR}/{user_id}/{USER_SPEECH_NAME}")

	def default_agent_speech_path(self, user_id: str) -> str:
		return str(self._root / f"{USER_TMP_DIR}/{user_id}/{AGENT_SPEECH_NAME}")

	def default_tmp_file_path(self, user_id: str, file_name: str) -> str:
		date, _ = get_time()
		tmp_dir = self._root / f"{USER_TMP_DIR}/{user_id}/{date}"
		tmp_path = str(tmp_dir / file_name)
		return tmp_path

	def put_agent_reply(
		self,
		user_id: str,
		reply_str: str,
		references: List[str] = None,
		reply_in_speech: bool = False,
		inner_chat: bool = False,
	):
		self.account_manager.check_valid_user(user_id=user_id)
		if not reply_in_speech:
			reply = ServerReply(
				reply_text=reply_str,
				references=references,
				valid=True,
				inner_chat=inner_chat,
			)
			self.agent_reply_buffer[user_id] = reply
			return

		speech_path = self.default_agent_speech_path(user_id=user_id)

		TTSWorker.transform(text=reply_str, speech_path=speech_path)
		reply = ServerSpeechReply(
			reply_speech_path=speech_path,
			inner_chat=inner_chat,
			references=references,
			valid=True,
		)
		self.agent_reply_buffer[user_id] = reply
		with open("/root/zhisan/Labridge/speech_final.txt", "w") as f:
			f.write("Finish.")

	def get_agent_reply(self, user_id: str) -> Union[ServerReply, ServerSpeechReply]:
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
