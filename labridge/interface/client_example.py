import websockets
import asyncio
import json
from pathlib import Path

from labridge.interface.types import READY_FOR_UPLOAD, UPLOAD_SUCCESS, \
	ServerDownloadMessage, ServerReply, CLIENT_READY_FOR_DOWNLOAD
from websockets import ConnectionClosed


async def chat_with_file_pipeline():
	user_id = "zhisan"
	uri = f"ws://127.0.0.1:6006/ws/upload/{user_id}"

	async with websockets.connect(uri) as websocket:
		while True:
			file_path = input("File Path: ")
			attached_user_query = input("User query: ")
			file_name = Path(file_path).name
			header_required_info = {
				"user_id": user_id,
				"file_name": file_name,
				"attached_text": attached_user_query,
			}
			# Send the request header
			await websocket.send(json.dumps(header_required_info))

			# Wait for the server reply
			server_reply_json = await websocket.recv()
			server_reply = ServerReply.loads(dumped_str=server_reply_json)
			if server_reply.error:
				print(server_reply.error)
				continue

			reply_text = server_reply.reply_text
			if reply_text.lower() == READY_FOR_UPLOAD.lower():
				# Upload file data.
				f_data = open(file_path, "rb").read()
				await websocket.send(f_data)
				# Wait for the server's result
				server_result_json = await websocket.recv()
				server_result = ServerReply.loads(dumped_str=server_result_json)
				result_text = server_result.reply_text
				if result_text.lower() == UPLOAD_SUCCESS.lower():
					print(f"{file_name} successfully uploaded.")
				else:
					print(f"Uploading of {file_name} failed.")

async def download_pipeline():
	user_id = "zhisan"
	uri = f"ws://127.0.0.1:6006/ws/download/{user_id}"

	async with websockets.connect(uri) as websocket:
		while True:
			file_path = input("File Path: ")
			header_required_info = {
				"user_id": user_id,
				"file_path": file_path,
			}

			# Send the request header
			await websocket.send(json.dumps(header_required_info))

			# Wait for the server reply
			server_reply_json = await websocket.recv()
			server_reply = ServerReply.loads(dumped_str=server_reply_json)
			if server_reply.error:
				print(server_reply.error)
				continue

			reply_text = server_reply.reply_text
			msg = ServerDownloadMessage.loads(dumped_str=reply_text)
			file_name = msg.file_name
			# Send Ready to download
			await websocket.send(CLIENT_READY_FOR_DOWNLOAD)

			# Download
			f_bytes = await websocket.recv()

			# Save the file
			save_path = str(Path("/root/zhisan/Labridge/documents") / file_name)
			with open(save_path, "wb") as f:
				f.write(f_bytes)

async def chat_text_pipeline():
	user_id = "zhisan"
	uri = f"ws://127.0.0.1:6006/ws/chat_text/{user_id}"

	while True:
		try:
			async with websockets.connect(
					uri,
					ping_interval=1000,
					ping_timeout=1000,
					close_timeout=1000,
					timeout=1000,
			) as websocket:
				while True:
					msg = input("User: ")
					try:
						await websocket.send(msg)

						received = False
						while not received:
							server_reply_json = await websocket.recv()
							server_reply = ServerReply.loads(dumped_str=server_reply_json)
							print(server_reply.reply_text)
							if server_reply.reply_text != "Keeping alive" or server_reply.error:
								break

						if server_reply.error:
							print(server_reply.error)
							continue
						print("Server: ", f"{server_reply.reply_text}")
					except ConnectionClosed:
						print("The connection abnormally close.")
						await asyncio.sleep(1)
						print("Reconnecting ...")
						break
		except ConnectionRefusedError as e:
			print("The server refused")
			break

async def chat_speech_pipeline():
	user_id = "zhisan"


if __name__ == "__main__":
	asyncio.get_event_loop().run_until_complete(chat_text_pipeline())


