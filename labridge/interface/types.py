import json
from pydantic import BaseModel
from pathlib import Path
from labridge.common.utils.time import get_time

from typing import List, Optional


READY_FOR_UPLOAD = "ReadyForUpload"
UPLOAD_SUCCESS = "UploadSuccess"
CLIENT_READY_FOR_DOWNLOAD = "ReadyForDownload"

UPLOAD_FILE_TMP_DIR = "tmp"


class BaseClientMessage(BaseModel):
	user_id: str


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