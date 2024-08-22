import torch

from llama_index.llms.huggingface import HuggingFaceLLM
from transformers.utils.quantization_config import BitsAndBytesConfig

from .zhipu import ZhiPuLLM
from .mindspore_models import MindsporeLLM



DEFAULT_SERVER_LLM_PATH = '/root/autodl-tmp/Qwen2-7B-Instruct'
DEFAULT_SERVER_CONTEXT_WINDOW = 16000
DEFAULT_SERVER_MAX_NEW_TOKENS = 1024

DEFAULT_SERVER_GENERATE_KWARGS = {"temperature": 0.01, "top_k": 4, "top_p": 0.95}


def completion_to_prompt(completion):
	# print(completion)
	return f"<|system|>\n</s>\n<|user|>\n{completion}</s>\n<|assistant|>\n"


def messages_to_prompt(messages):
	prompt = ""
	for message in messages:
		if message.role == "system":
			prompt += f"<|system|>\n{message.content}</s>\n"
		elif message.role == "user":
			prompt += f"<|user|>\n{message.content}</s>\n"
		elif message.role == "assistant":
			prompt += f"<|assistant|>\n{message.content}</s>\n"

	# ensure we start with a system prompt, insert blank if needed
	if not prompt.startswith("<|system|>\n"):
		prompt = "<|system|>\n</s>\n" + prompt

	# add final assistant prompt
	prompt = prompt + "<|assistant|>\n"
	# print(prompt)
	# print(messages)
	return prompt


def load_server_llm(
	model_path: str = None,
	context_window: int = None,
	max_new_tokens: int = None,
	generate_kwargs: dict = None,
	load_in_8bit: bool = True,
	use_api: bool = False,
	use_mindspore: bool = False,
):
	model_path = model_path or DEFAULT_SERVER_LLM_PATH
	context_window = context_window or DEFAULT_SERVER_CONTEXT_WINDOW
	max_new_tokens = max_new_tokens or DEFAULT_SERVER_MAX_NEW_TOKENS
	generate_kwargs = generate_kwargs or DEFAULT_SERVER_GENERATE_KWARGS
	if use_api:
		llm = ZhiPuLLM()
		return llm

	if use_mindspore:
		llm = MindsporeLLM()
		return llm

	quantization_config = BitsAndBytesConfig(
		load_in_8bit=load_in_8bit,
		bnb_4bit_compute_dtype=torch.bfloat16,
		bnb_4bit_quant_type="nf4",
		bnb_4bit_use_double_quant=True,
	)

	model_kwargs = {
		"trust_remote_code": True,
		"quantization_config": quantization_config,
	}

	llm = HuggingFaceLLM(
		model_name=model_path,
		tokenizer_name=model_path,
		context_window=context_window,
		max_new_tokens=max_new_tokens,
		generate_kwargs=generate_kwargs,
		device_map="cuda",
		messages_to_prompt=messages_to_prompt,
		completion_to_prompt=completion_to_prompt,
		model_kwargs=model_kwargs
	)
	return llm
