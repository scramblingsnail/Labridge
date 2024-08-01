from llama_index.core.llms.callbacks import llm_completion_callback
from llama_index.core.llms import CustomLLM
from llama_index.core.base.llms.types import (
	LLMMetadata,
	CompletionResponse,
	CompletionResponseGen,
)
from llama_index.core.base.embeddings.base import (
	BaseEmbedding,
	Embedding,
)

from typing import Any
from zhipuai import ZhipuAI


client = ZhipuAI(api_key="71eff193fe38f344074931101d510511.EYE7gbcTFUFQdfe4")


class ZhiPuLLM(CustomLLM):
	context_window: int = 16000
	num_output: int = 1024
	model_name: str = "glm-4"
	is_chat_model: bool = False

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
		messages = [
			{
				"role": "user",
				"content": prompt,
			}
		]
		response = client.chat.completions.create(
			model=self.model_name,
			messages=messages,
		)
		response_text = response.choices[0].message.content
		return CompletionResponse(text=response_text)

	@llm_completion_callback()
	def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
		messages = [
			{
				"role": "user",
				"content": prompt,
			}
		]
		response = client.chat.completions.create(model=self.model_name, messages=messages, )
		response_text = response.choices[0].message.content
		gen_tokens = ""
		for token in response_text:
			gen_tokens += token
			yield CompletionResponse(text=response, delta=token)

class ZhiPuEmbedding(BaseEmbedding):
	model_name = "embedding-2"

	def _get_query_embedding(self, query: str) -> Embedding:
		response = client.embeddings.create(
			model=self.model_name,
			input=query)
		return response.data[0].embedding

	async def _aget_query_embedding(self, query: str) -> Embedding:
		return self._get_query_embedding(query=query)

	def _get_text_embedding(self, text: str) -> Embedding:
		return self._get_query_embedding(query=text)
