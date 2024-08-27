import websockets
import asyncio
import json
import httpx

from httpx import URL, Request

from websockets import ConnectionClosed
from typing import Optional, List
from pydantic import BaseModel


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
		监听 Agent 回复，以及在 Inner_chat 的情况下，返回用户回复至。

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
			# 在 inner_chat 的情况下，将用户的回复 post 到 post_tool_info_url。
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


if __name__ == "__main__":
	asyncio.get_event_loop().run_until_complete(chat_with_text())

	# async def loop1 ():
	# 	a = 0
	# 	while True:
	# 		await asyncio.sleep(1)