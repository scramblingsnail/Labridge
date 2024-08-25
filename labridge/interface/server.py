import asyncio

import uvicorn
from fastapi import WebSocket, WebSocketDisconnect, FastAPI
# from fastapi.middleware.timeout import TimeoutMiddleware

from labridge.interface.server_backend import SocketManager
from labridge.interface.types import (
	FileWithTextMessage,
	ChatTextMessage,
	DownloadRequest,
	CLIENT_READY_FOR_DOWNLOAD,
	ServerReply,
	ChatSpeechMessage,
	ServerSpeechReply,
)
from labridge.interface.utils import save_temporary_file, read_server_file
from labridge.agent.chat_agent import ChatAgent

from pydantic import BaseModel


app = FastAPI()


# app.add_middleware(TimeoutMiddleware, timeout=timedelta(seconds=5))



@app.get("/")
async def get_home():
	return ChatTextMessage(text="Hello, This is the home.")


@app.websocket("/ws/upload/{user_id}")
async def websocket_chat_with_file(websocket: WebSocket, user_id: str):
	try:
		await SocketManager.upload_connect(websocket=websocket, user_id=user_id)
	except Exception as e:
		await websocket.accept()
		error_reply = ServerReply(reply_text=f"{e}", error=f"{e}")
		await websocket.send_text(error_reply.dumps())

	async def keep_alive(ws):
		keep_replay = ServerReply(reply_text="Keeping alive")
		while True:
			try:
				await ws.send_text(keep_replay.dumps())
				await asyncio.sleep(5)
			except:
				break

	try:
		asyncio.create_task(keep_alive(websocket))

		while True:
			# Receive the FileWithTextMessage
			file_header = await websocket.receive()
			try:
				request_str = file_header.get("text", None)
				if request_str is None:
					raise ValueError("Please send a request_str first.")

				msg = FileWithTextMessage.loads(dumped_str=request_str)
				if msg.user_id != user_id:
					raise ValueError("The user_id of request is not correct.")

				# Ready for uploading
				await SocketManager.permit_uploading(user_id=user_id)

				file_content = await websocket.receive()
				file_bytes = file_content.get("bytes", None)
				# Save file to temporary directory
				if file_bytes is None:
					raise ValueError("Please send file data after request.")

				f_path = save_temporary_file(
					user_id=msg.user_id,
					file_name=msg.file_name,
					file_bytes=file_bytes,
				)
				msg.set_file_path(f_path=f_path)

				# Chat with the agent
				reply = await ChatAgent.chat(user_message=msg)
				reply_json = reply.dumps()
				# Send reply to the client
				await websocket.send_text(reply_json)
			except Exception as e:
				reply_json = ServerReply(reply_text=f"{e}", error=f"{e}").dumps()
				await websocket.send_text(reply_json)
	except WebSocketDisconnect:
		SocketManager.upload_disconnect(user_id=user_id)
		print(f"The user disconnect.")

@app.websocket("/ws/download/{user_id}")
async def websocket_download(websocket: WebSocket, user_id: str):
	try:
		await SocketManager.download_connect(websocket=websocket, user_id=user_id)
	except Exception as e:
		await websocket.accept()
		error_reply = ServerReply(reply_text=f"{e}", error=f"{e}")
		await websocket.send_text(error_reply.dumps())
		return

	try:
		while True:
			# receive the request from client.
			request = await websocket.receive()
			try:
				request_str = request.get("text", None)
				if request_str is None:
					raise ValueError("Please send a request_str first.")

				# read the server file.
				download_rq = DownloadRequest.loads(dumped_str=request_str)
				f_bytes = read_server_file(file_path=download_rq.file_path)
				if f_bytes is None:
					raise ValueError(f"{download_rq.file_path} does not exist.")
				# inform the client to download.
				await SocketManager.inform_downloading(user_id=user_id, file_path=download_rq.file_path)
				# wait for the client's reply.
				client_reply = await websocket.receive_text()
				if client_reply.lower() == CLIENT_READY_FOR_DOWNLOAD.lower():
					# send the bytes.
					await websocket.send_bytes(f_bytes)
			except Exception as e:
				reply_json = ServerReply(reply_text=f"{e}", error=f"{e}").dumps()
				await websocket.send_text(reply_json)
	except WebSocketDisconnect:
		SocketManager.download_disconnect(user_id=user_id)
		print(f"The user disconnect.")
	return

@app.websocket("/ws/chat_text/{user_id}")
async def websocket_chat_text(websocket: WebSocket, user_id: str):
	import time

	try:
		await SocketManager.chat_text_connect(websocket=websocket, user_id=user_id)
	except Exception as e:
		await websocket.accept()
		error_reply = ServerReply(reply_text=f"{e}", error=f"{e}")
		await websocket.send_text(error_reply.dumps())
		return

	try:
		while True:
			msg = await websocket.receive()
			try:
				start_time = time.time()

				user_query = msg.get("text", None)
				if user_query is not None:
					user_msg = ChatTextMessage(user_id=user_id, text=user_query)
					reply = await ChatAgent.chat(user_message=user_msg)
					reply_json = reply.dumps()

					# reply_json = ServerReply(reply_text="hello!").dumps()

					end_time = time.time()

					print("Current QA duration: ", end_time - start_time)

					# Send back
					await websocket.send_text(reply_json)
			except Exception as e:
				reply_json = ServerReply(reply_text=f"{e}", error=f"{e}").dumps()
				await websocket.send_text(reply_json)
	except WebSocketDisconnect:
		SocketManager.chat_text_disconnect(user_id=user_id)
		raise ValueError("Disconnect .......")


@app.websocket("/ws/chat_speech/{user_id}")
async def websocket_chat_speech(websocket: WebSocket, user_id: str):
	try:
		await SocketManager.chat_speech_connect(websocket=websocket, user_id=user_id)
	except Exception as e:
		await websocket.accept()
		error_reply = ServerReply(reply_text=f"{e}", error=f"{e}")
		await websocket.send_text(error_reply.dumps())
		return

	try:
		while True:
			try:
				msg = await websocket.receive()
				file_bytes = msg.get("bytes", None)
				if file_bytes is None:
					raise ValueError("Please send the speech data bytes.")

				# TODO speech file name
				speech_file_name = f"speech.json"
				speech_path = save_temporary_file(
					user_id=user_id,
					file_name=speech_file_name,
					file_bytes=file_bytes,
				)
				user_msg = ChatSpeechMessage(speech_path=speech_path)

				reply: ServerSpeechReply = ChatAgent.chat(user_message=user_msg)
				reply_speech_path = reply.reply_speech_path

				reply_bytes = open(reply_speech_path, "rb").read()
				await websocket.send_bytes(reply_bytes)
			except Exception as e:
				reply_json = ServerReply(reply_text=f"{e}", error=f"{e}").dumps()
				await websocket.send_text(reply_json)

	except WebSocketDisconnect:
		SocketManager.chat_speech_disconnect(user_id=user_id)
		print(f"The user disconnect.")


if __name__ == "__main__":
	uvicorn.run(app, host='127.0.0.1', port=6006, workers=1, timeout_keep_alive=1000)


