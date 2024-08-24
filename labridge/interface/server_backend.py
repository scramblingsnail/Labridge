from fastapi import WebSocket
from pydantic import BaseModel
from enum import Enum
from pathlib import Path
from labridge.accounts.users import AccountManager
from typing import List, Dict, Any

from labridge.interface.types import READY_FOR_UPLOAD, UPLOAD_SUCCESS, \
	ServerDownloadMessage, ServerReply



class ClientSocketType(Enum):
	CHAT_TEXT = "chat_text"
	CHAT_SPEECH = "chat_speech"
	UPLOAD = "upload"
	DOWNLOAD = "download"


class WebSocketClient(object):
	def __init__(
		self,
		user_id: str,
		chat_text_socket: WebSocket = None,
		chat_speech_socket: WebSocket = None,
		upload_socket: WebSocket = None,
		download_socket: WebSocket = None,
	):
		self.user_id = user_id
		self.chat_text_socket = chat_text_socket
		self.chat_speech_socket = chat_speech_socket
		self.upload_socket = upload_socket
		self.download_socket = download_socket

	async def chat_text_connect(self, websocket: WebSocket):
		await websocket.accept()
		self.chat_text_socket = websocket

	async def chat_speech_connect(self, websocket: WebSocket):
		await websocket.accept()
		self.chat_speech_socket = websocket

	async def upload_connect(self, websocket: WebSocket):
		await websocket.accept()
		self.upload_socket = websocket

	async def download_connect(self, websocket: WebSocket):
		await websocket.accept()
		self.download_socket = websocket

	def chat_text_disconnect(self):
		self.chat_text_socket = None

	def chat_speech_disconnect(self):
		self.chat_speech_socket = None

	def upload_disconnect(self):
		self.upload_socket = None

	def download_disconnect(self):
		self.download_socket = None

	async def permit_uploading(self):
		if self.upload_socket:
			reply = ServerReply(reply_text=READY_FOR_UPLOAD).dumps()
			await self.upload_socket.send_text(reply)

	async def inform_downloading(self, file_path: str):
		if self.download_socket:
			file_name = Path(file_path).name
			download_message = ServerDownloadMessage(file_name=file_name).dumps()
			reply = ServerReply(reply_text=download_message).dumps()
			await self.download_socket.send_text(reply)


class WebSocketManager(object):
	r""" Manage the websockets of clients. """
	def __init__(self):
		self.clients: Dict[str, WebSocketClient] = dict()
		self.account_manager = AccountManager()

	async def chat_text_connect(self, websocket: WebSocket, user_id: str):
		try:
			self.account_manager.check_valid_user(user_id=user_id)
			if user_id not in self.clients.keys():
				self.clients[user_id] = WebSocketClient(user_id=user_id)
			await self.clients[user_id].chat_text_connect(websocket=websocket)
		except Exception as e:
			raise Exception(f"Error: {e}.")

	async def chat_speech_connect(self, websocket: WebSocket, user_id: str):
		try:
			self.account_manager.check_valid_user(user_id=user_id)
			if user_id not in self.clients.keys():
				self.clients[user_id] = WebSocketClient(user_id=user_id)
			await self.clients[user_id].chat_speech_connect(websocket=websocket)
		except Exception as e:
			raise Exception(f"Error: {e}.")

	async def upload_connect(self, websocket: WebSocket, user_id: str):
		try:
			self.account_manager.check_valid_user(user_id=user_id)
			if user_id not in self.clients.keys():
				self.clients[user_id] = WebSocketClient(user_id=user_id)
			await self.clients[user_id].upload_connect(websocket=websocket)
		except Exception as e:
			raise Exception(f"Error: {e}.")

	async def download_connect(self, websocket: WebSocket, user_id: str):
		try:
			self.account_manager.check_valid_user(user_id=user_id)
			if user_id not in self.clients.keys():
				self.clients[user_id] = WebSocketClient(user_id=user_id)
			await self.clients[user_id].download_connect(websocket=websocket)
		except Exception as e:
			raise Exception(f"Error: {e}.")

	def chat_text_disconnect(self, user_id: str):
		if self.clients[user_id]:
			self.clients[user_id].chat_text_disconnect()

	def chat_speech_disconnect(self, user_id: str):
		if self.clients[user_id]:
			self.clients[user_id].chat_speech_disconnect()

	def upload_disconnect(self, user_id: str):
		if self.clients[user_id]:
			self.clients[user_id].upload_disconnect()

	def download_disconnect(self, user_id: str):
		if self.clients[user_id]:
			self.clients[user_id].download_disconnect()

	async def permit_uploading(self, user_id: str):
		client = self.clients.get(user_id, None)
		if client:
			await client.permit_uploading()

	async def inform_downloading(self, user_id: str, file_path: str):
		client = self.clients.get(user_id, None)
		if client:
			await client.inform_downloading(file_path=file_path)

	async def send_text_to_client(
		self,
		user_id: str,
		text: str,
		socket_type: ClientSocketType = ClientSocketType.CHAT_TEXT,
	):
		client = self.clients.get(user_id, None)
		if client:
			if socket_type == ClientSocketType.CHAT_TEXT:
				websocket = client.chat_text_socket
			elif socket_type == ClientSocketType.CHAT_SPEECH:
				websocket = client.chat_speech_socket
			elif socket_type == ClientSocketType.UPLOAD:
				websocket = client.upload_socket
			elif socket_type == ClientSocketType.DOWNLOAD:
				websocket = client.download_socket
			else:
				raise ValueError("Invalid socket_type.")

			if websocket:
				reply = ServerReply(reply_text=text).dumps()
				await websocket.send_text(reply)

	async def receive_text_from_client(
		self,
		user_id: str,
		socket_type: ClientSocketType = ClientSocketType.CHAT_TEXT,
	) -> str:
		client = self.clients.get(user_id, None)
		if client:
			if socket_type == ClientSocketType.CHAT_TEXT:
				websocket = client.chat_text_socket
			elif socket_type == ClientSocketType.CHAT_SPEECH:
				websocket = client.chat_speech_socket
			elif socket_type == ClientSocketType.UPLOAD:
				websocket = client.upload_socket
			elif socket_type == ClientSocketType.DOWNLOAD:
				websocket = client.download_socket
			else:
				raise ValueError("Invalid socket_type.")

			if websocket:
				user_msg = await websocket.receive_text()
				return user_msg
		raise ValueError(f"Invalid connection to user {user_id}.")

	async def send_bytes_to_client(self, user_id: str, msg_bytes: bytes, socket_type: ClientSocketType):
		client = self.clients.get(user_id, None)
		if client:
			if socket_type == ClientSocketType.DOWNLOAD:
				websocket = client.upload_socket
			else:
				raise ValueError(f"{socket_type} does not support sending files.")

			if websocket:
				await websocket.send_bytes(msg_bytes)

SocketManager = WebSocketManager()
