import mindspore
from mindnlp.transformers import AutoModelForCausalLM, AutoTokenizer
from llama_index.core.llms.callbacks import llm_completion_callback
from llama_index.core.base.llms.types import (
	LLMMetadata,
	CompletionResponse,
	CompletionResponseGen,
)

from llama_index.core.llms.custom import CustomLLM
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.constants import DEFAULT_CONTEXT_WINDOW, DEFAULT_NUM_OUTPUTS, DEFAULT_EMBED_BATCH_SIZE
from typing import Any, Callable, Dict, List, Optional, Sequence, Union

from llama_index.core.base.embeddings.base import (
    DEFAULT_EMBED_BATCH_SIZE,
    BaseEmbedding,
    Embedding,
)
from llama_index.core.bridge.pydantic import Field, PrivateAttr
from llama_index.core.utils import get_cache_dir
from llama_index.embeddings.huggingface.utils import (
    get_query_instruct_for_model_name,
    get_text_instruct_for_model_name,
)
from mindnlp.sentence.sentence_transformer import SentenceTransformer


DEFAULT_MINDSPORE_MODEL = "ZhipuAI/glm-4-9b-chat"
DEFAULT_MINDSPORE_EMBEDDING = "BAAI/bge-large-zh-v1.5"

DEFAULT_MINDSPORE_GENERATE_KWARGS = {
	"max_length": 100,
	"do_sample": True,
	"top_k": 4,
	"temperature": 0.01,
	"top_p": 0.95,
}


class MindsporeLLM(CustomLLM):
	num_output: int = 1024

	model_name: str = Field(
		default=DEFAULT_MINDSPORE_MODEL,
		description=(
			"The model name to use from HuggingFace. "
		),
	)
	tokenizer_name: str = Field(
		default=DEFAULT_MINDSPORE_MODEL,
		description=(
			"The name of the tokenizer to use from HuggingFace. "
			"Unused if `tokenizer` is passed in directly."
		),
	)
	context_window: int = Field(
		default=DEFAULT_CONTEXT_WINDOW,
		description="The maximum number of tokens available for input.",
		gt=0,
	)
	max_new_tokens: int = Field(
		default=DEFAULT_NUM_OUTPUTS,
		description="The maximum number of tokens to generate.",
		gt=0,
	)
	generate_kwargs: dict = Field(
		default=DEFAULT_MINDSPORE_GENERATE_KWARGS,
		# default_factory=dict,
		description="The kwargs to pass to the model during generation.",
	)
	is_chat_model: bool = Field(
		default=False,
		description=(
				LLMMetadata.__fields__["is_chat_model"].field_info.description
				+ " Be sure to verify that you either pass an appropriate tokenizer "
				"that can convert prompts to properly formatted chat messages or a "
				"`messages_to_prompt` that does so."
		),
	)

	_model: Any = PrivateAttr()
	_tokenizer: Any = PrivateAttr()

	def __init__(
		self,
		model_name: str = DEFAULT_MINDSPORE_MODEL,
		tokenizer_name: str = DEFAULT_MINDSPORE_MODEL,
		context_window: int = DEFAULT_CONTEXT_WINDOW,
		max_new_tokens: int = DEFAULT_NUM_OUTPUTS,
		generate_kwargs: Optional[dict] = None,
		is_chat_model: Optional[bool] = False,
		system_prompt: str = "",
		messages_to_prompt: Optional[Callable[[Sequence[ChatMessage]], str]] = None,
		completion_to_prompt: Optional[Callable[[str], str]] = None,
	):
		self._model = AutoModelForCausalLM.from_pretrained(
			pretrained_model_name_or_path=model_name,
			mirror='modelscope',
			ms_dtype=mindspore.float16,
		).eval()

		config_dict = self._model.config.to_dict()
		model_context_window = int(
			config_dict.get("max_position_embeddings", context_window)
		)
		if model_context_window and model_context_window < context_window:
			context_window = model_context_window

		self._tokenizer = AutoTokenizer.from_pretrained(
			pretrained_model_name_or_path=model_name,
			mirror='modelscope',
			max_length=context_window,
		)
		super().__init__(
			context_window=context_window,
			max_new_tokens=max_new_tokens,
			tokenizer_name=tokenizer_name,
			model_name=model_name,
			generate_kwargs=generate_kwargs or DEFAULT_MINDSPORE_GENERATE_KWARGS,
			is_chat_model=is_chat_model,
			system_prompt = system_prompt,
			messages_to_prompt=messages_to_prompt,
			completion_to_prompt=completion_to_prompt,
		)

	@property
	def metadata(self) -> LLMMetadata:
		"""Get LLM metadata."""
		return LLMMetadata(
			context_window=self.context_window,
			num_output=self.max_new_tokens,
			model_name=self.model_name,
			is_chat_model=self.is_chat_model,
		)

	@llm_completion_callback()
	def complete(self, prompt: str, **kwargs: Any) -> CompletionResponse:
		inputs = self._tokenizer(prompt, return_tensors="ms")
		outputs = self._model.generate(**inputs, **self.generate_kwargs)
		outputs = outputs[:, inputs['input_ids'].shape[1]:]
		response_text = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
		return CompletionResponse(text=response_text)

	@llm_completion_callback()
	def stream_complete(self, prompt: str, **kwargs: Any) -> CompletionResponseGen:
		inputs = self._tokenizer(prompt, return_tensors="ms")
		outputs = self._model.generate(**inputs, **self.generate_kwargs)
		outputs = outputs[:, inputs['input_ids'].shape[1]:]
		response_text = self._tokenizer.decode(outputs[0], skip_special_tokens=True)
		gen_tokens = ""
		for token in response_text:
			gen_tokens += token
			yield CompletionResponse(text=gen_tokens, delta=token)

class MindsporeEmbedding(BaseEmbedding):
	cache_folder: Optional[str] = Field(
		description="Cache folder for Hugging Face files."
	)
	normalize: bool = Field(
		default=True,
		description="Normalize embeddings or not."
	)
	query_instruction: Optional[str] = Field(
		description="Instruction to prepend to query text."
	)
	text_instruction: Optional[str] = Field(
		description="Instruction to prepend to text."
	)
	_embed_model: Any = PrivateAttr()
	_device: str = PrivateAttr()

	def __init__(
		self,
		model_name: str = DEFAULT_MINDSPORE_EMBEDDING,
		device: str = "CPU",
		query_instruction: Optional[str] = None,
		text_instruction: Optional[str] = None,
		normalize: bool = True,
		embed_batch_size: int = DEFAULT_EMBED_BATCH_SIZE,
		cache_folder: Optional[str] = None,
	):
		super().__init__(
			model_name=model_name,
			embed_batch_size=embed_batch_size,
			normalize = normalize,
		)
		cache_folder = cache_folder or get_cache_dir()
		self._device = device

		self._embed_model = SentenceTransformer(
			model_name_or_path=model_name,
			device="CPU",
			cache_folder=cache_folder,
			prompts={
				"query": query_instruction
						 or get_query_instruct_for_model_name(model_name),
				"text": text_instruction
						or get_text_instruct_for_model_name(model_name),
			}
		)


	def _get_query_embedding(self, query: str) -> Embedding:
		return self._embed(query, prompt_name="query")

	def _embed(
		self,
		sentences: str,
		prompt_name: Optional[str] = None,
	) -> Embedding:
		embedding = self._embed_model.encode(
			sentences,
			prompt_name=prompt_name,
			batch_size=self.embed_batch_size,
			normalize_embeddings=True,
		)
		return list(embedding.numpy())

	async def _aget_query_embedding(self, query: str) -> Embedding:
		return self._get_query_embedding(query=query)

	def _get_text_embedding(self, text: str) -> Embedding:
		return self._embed(text, prompt_name="text")


if __name__ == "__main__":
	llm = MindsporeLLM()
	response = llm.complete(prompt="Introduce the PPO algorithm.")
	print(response.text)

	embed = MindsporeEmbedding(
		model_name = "/root/autodl-tmp/bge-large-zh-v1.5",
		device = "CPU",
		query_instruction = None,
		text_instruction = None,
		normalize = True,
		embed_batch_size = DEFAULT_EMBED_BATCH_SIZE,
		cache_folder = None,
	)
	embedding_list = embed.get_query_embedding("Introduce the PPO algorithm.")
	print(embedding_list)
