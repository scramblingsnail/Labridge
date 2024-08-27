import websockets
import asyncio
import json
import httpx

from httpx import URL, Request

import aiohttp

from websockets import ConnectionClosed
from typing import Optional, List
from pydantic import BaseModel



async def chat_with_speech():
	base_url = "http://127.0.0.1:6006"
	user_id = "杨再正"

	post_speech_router = f"/users/{user_id}/chat_speech"
	get_response_router = f"/users/{user_id}/response"
	download_file_router = f"/users/{user_id}/files/bytes"

	post_speech_url = URL(f"{base_url}{post_speech_router}")
	get_response_url = URL(f"{base_url}{get_response_router}")


	client = httpx.AsyncClient(timeout=100)

	async def query_in_speech(speech_path: str):
		speech_data = open(speech_path, "rb").read()

		await client.send(
			request=Request(
				method="post",
				url=post_speech_url,
				files={
					"file": speech_data
				}
			)
		)
		print("Finished.")

	async def get_response():
		r"""
		监听 Agent 回复。

		Returns:

		"""
		while True:
			reply = await client.get(url=get_response_url, )
			print(reply.text)

			# 等待标识为 'valid' 的 agent回复。
			if reply.text:
				reply_dict = json.loads(reply.text)
				valid = reply_dict["valid"]
				if valid:
					# 展示 Agent 回复
					print(reply_dict["reply_speech_path"])
					break
			await asyncio.sleep(1)

		# 根据 reply_speech_path 从 server 下载音频文件。
		reply_speech_path = reply_dict.get("reply_speech_path", None)
		if reply_speech_path:
			# 从服务器下载文件。
			print(f"{base_url}{download_file_router}")

			download_request = {
				"filepath": reply_speech_path
			}

			download_response = await client.post(
				url = URL(f"{base_url}{download_file_router}"),
				json=download_request,
			)
			f_bytes = download_response.content
			with open("./agent_reply.pcm", "wb") as f:
				f.write(f_bytes)

	await asyncio.gather(
		query_in_speech(
			speech_path="/root/zhisan/Labridge/labridge/interface/query_1.pcm",
		),
		get_response(),
	)


async def chat_with_text():
	base_url = "http://127.0.0.1:6006"
	user_id="杨再正"

	post_text_router = f"/users/{user_id}/chat_text"
	get_response_router = f"/users/{user_id}/response"
	inner_chat_text_router = f"/users/{user_id}/inner_chat_text"

	post_text_url = URL(f"{base_url}{post_text_router}")
	get_response_url = URL(f"{base_url}{get_response_router}")
	post_tool_info_url = URL(f"{base_url}{inner_chat_text_router}")

	client = httpx.AsyncClient(timeout=100)

	async def query(usr_msg):
		r"""
		这是一轮 QA 的开始，将用户消息 Post 到 post_text_url, 服务器调用 agent.chat。

		Args:
			usr_msg:

		Returns:

		"""
		await client.send(
			request=Request(
				method="post",
				url=post_text_url,
				json=usr_msg,
			)
		)
		print("Finish")

	async def get_response():
		r"""
		监听 Agent 回复，以及在 Inner_chat 的情况下，返回用户回复至 对应的 Inner URL。

		Returns:

		"""
		async def single_get():
			while True:
				reply = await client.get(url=get_response_url, )
				print(reply.text)

				# 等待标识为 'valid' 的 agent回复。
				if reply.text:
					reply_dict = json.loads(reply.text)
					valid = reply_dict["valid"]
					if valid:
						# 展示 Agent 回复
						print(reply_dict["reply_text"])
						break
				await asyncio.sleep(1)
			return reply_dict

		# 等待第一次回复。
		re_dict = await single_get()
		inner_chat = re_dict["inner_chat"]

		print("inner: ", inner_chat)

		# 若为 一次Chat内部的 Agent 回复：
		while inner_chat:
			# 在一次Chat的内部，如Agent调用工具过程中需要收集用户信息，于是返回了收集信息的回复。
			# 在 inner_chat 的情况下，将用户的回复 post 到 相应的 Inner URL。
			info = input("User Info: ")
			await client.send(
				request=Request(
					method="post",
					url=post_tool_info_url,
					json={
						"text": info,
					},
				)
			)
			re_dict = await single_get()
			inner_chat = re_dict["inner_chat"]
			# 展示 Agent回复。
			print(re_dict["reply_text"])
		# agent 回复的不是 inner_chat 标识， 这一轮QA结束。
		print("This QA finishes.")


	while True:
		user_query = input("User: ")
		msg = {
			"text": user_query,
		}
		await asyncio.gather(query(msg), get_response())


async def download_file():
	base_url = "http://127.0.0.1:6006"
	user_id="杨再正"
	download_file_router = f"/users/{user_id}/files/bytes"

	file_path = "/root/zhisan/Labridge/labridge/interface/query_1.pcm"
	download_request = {"filepath": file_path}

	client = httpx.AsyncClient(timeout=100)

	download_response = await client.post(
		url=URL(f"{base_url}{download_file_router}"),
		json=download_request
	)
	f_bytes = download_response.content
	with open("./test_download.pcm", "wb") as f:
		f.write(f_bytes)


if __name__ == "__main__":
	# asyncio.get_event_loop().run_until_complete(chat_with_text())

	asyncio.get_event_loop().run_until_complete(chat_with_speech())

	# asyncio.get_event_loop().run_until_complete(download_file())