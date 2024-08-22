import asyncio

import httpx
from httpx import Timeout, URL, Limits, Request
import json
from enum import Enum

from llama_index.core.bridge.pydantic import Field, PrivateAttr, BaseModel
from llama_index.core.llms.callbacks import llm_completion_callback
from llama_index.core.llms import CustomLLM
from llama_index.core.base.llms.types import (
	LLMMetadata,
	CompletionResponse,
	CompletionResponseGen,
)

from typing import Any
from typing import Union, List


DEFAULT_LLM_TIMEOUT = Timeout(timeout=600)
DEFAULT_LLM_LIMITS = Limits(max_connections=100, max_keepalive_connections=20)

DEFAULT_BASE_URL = "http://127.0.0.1:6006"
DEFAULT_LLM_URL = "http://127.0.0.1:6006/user_input"
DEFAULT_ASYNC_LLM_URL = "http://127.0.0.1:6006/async_user_input"


class RemoteModelType(Enum):
	LLM = "llm"
	Embed = "embedding"

class RemoteModelInput(BaseModel):
	text: str

class RemoteModelOutput(BaseModel):
	model_type: RemoteModelType
	output: Union[str, List[float]]


class ModelClient(object):
	def __init__(
		self,
		base_url: URL,
		model_type: RemoteModelType,
		timeout: Timeout = None,
		limits: Limits = None,
	):
		self._model_type = model_type
		self._timeout = timeout or DEFAULT_LLM_TIMEOUT
		self._limits = limits or DEFAULT_LLM_LIMITS
		self._client = httpx.Client(
			base_url=base_url,
			timeout=self._timeout,
			limits=self._limits,
		)

	def formatted_input(self, input_str: str) -> dict:
		return {
			"text": input_str,
		}

	def request(self, url: URL, input_str: str):
		query = self.formatted_input(input_str=input_str)

		response = self._client.send(
			request=Request(
				method="post",
				url=url,
				json=query
			)
		)
		output_dict = json.loads(response.text)
		output = output_dict["output"]
		return output


class AsyncModelClient(object):
	def __init__(
		self,
		model_type: RemoteModelType,
		timeout: Timeout = None,
		limits: Limits = None,
	):
		self._model_type = model_type
		self._timeout = timeout or DEFAULT_LLM_TIMEOUT
		self._limits = limits or DEFAULT_LLM_LIMITS
		self._client = httpx.AsyncClient(
			timeout=self._timeout,
			limits=self._limits,
		)

	def formatted_input(self, input_str: str) -> dict:
		return {
			"text": input_str,
		}

	async def arequest(self, url: URL, input_str: str):
		query = self.formatted_input(input_str=input_str)

		response = await self._client.send(
			request=Request(
				method="post",
				url=url,
				json=query
			)
		)
		output_dict = json.loads(response.text)
		output = output_dict["output"]
		return output


class RemoteLLM(CustomLLM):
	context_window: int = 16000 # useless
	num_output: int = 1024	# useless
	model_name: str = "remote"
	is_chat_model: bool = False

	base_url: str = Field(
		default=DEFAULT_BASE_URL,
		description="Base URL",
	)
	llm_url: str = Field(
		default=DEFAULT_LLM_URL,
		description="URL for receiving local inputs"
	)
	async_llm_url: str = Field(
		default=DEFAULT_ASYNC_LLM_URL,
		description="URL for asynchronously receiving local inputs"
	)

	_client: ModelClient = PrivateAttr()
	_async_client: AsyncModelClient = PrivateAttr()

	def __init__(
		self,
		base_url: str,
		llm_url: str,
		async_llm_url: str,
		context_window: int = 16000,
		num_output: int = 1024,
		model_name: str = "remote",
		is_chat_model: bool = False,

	):
		base_url = base_url or DEFAULT_BASE_URL
		llm_url = llm_url or DEFAULT_LLM_URL
		async_llm_url = async_llm_url or DEFAULT_ASYNC_LLM_URL
		self._client = ModelClient(
			base_url=URL(base_url),
			model_type=RemoteModelType.LLM,
		)
		self._async_client = AsyncModelClient(
			model_type=RemoteModelType.LLM,
		)
		super().__init__(
			base_url=base_url,
			llm_url=llm_url,
			async_llm_url = async_llm_url,
			context_window=context_window,
			num_output=num_output,
			model_name=model_name,
			is_chat_model=is_chat_model,
		)

	@property
	def metadata(self) -> LLMMetadata:
		"""Get LLM metadata."""
		return LLMMetadata(
			context_window=self.context_window,
			num_output=self.num_output,
			model_name=self.model_name,
		)

	@llm_completion_callback()
	def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
		try:
			response = self._client.request(
				url=URL(self.llm_url),
				input_str=prompt,
			)
			return CompletionResponse(text=response)
		except Exception as e:
			return CompletionResponse(text=e)


	@llm_completion_callback()
	async def acomplete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
		try:
			print("User: ", prompt)
			response = await self._async_client.arequest(
				url=URL(self.async_llm_url),
				input_str=prompt,
			)
			return CompletionResponse(text=response)
		except Exception as e:
			return CompletionResponse(text=e)

	@llm_completion_callback()
	def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
		try:
			response = self._client.request(
				url=URL(self.llm_url),
				input_str=prompt,
			)
		except Exception as e:
			response = e

		gen_tokens = ""
		for token in response:
			gen_tokens += token
			yield CompletionResponse(text=response, delta=token)


if __name__ == "__main__":
	llm = RemoteLLM(
		base_url=DEFAULT_BASE_URL,
		llm_url=DEFAULT_LLM_URL,
		async_llm_url=DEFAULT_ASYNC_LLM_URL,
	)

	# query_str = "你好呀，你叫什么名字？"
	# ss = llm.complete(query_str)
	# print(ss)

	query_str_1 = "介绍一下PPO算法"
	query_str_2 = "介绍一下SAC算法"

	async def main():
		task1 = asyncio.create_task(
			llm.acomplete(query_str_1)
		)
		task2 = asyncio.create_task(
			llm.acomplete(query_str_2)
		)

		answer_1 = await task1
		answer_2 = await task2

		print(">>> Answer 1: \n", answer_1)
		print(">>> Answer 2: \n", answer_2)

	asyncio.run(main())
