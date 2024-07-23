import torch

from llama_index.llms.huggingface import HuggingFaceLLM
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from transformers.utils.quantization_config import BitsAndBytesConfig
from llama_index.core.postprocessor import SentenceTransformerRerank


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


def get_reranker(reranker_path: str = None, rerank_top_n: int = None):
	reranker_path = reranker_path or "/root/autodl-tmp/bge-reranker-large"
	rerank_top_n = rerank_top_n or 100
	return SentenceTransformerRerank(model=reranker_path, top_n=rerank_top_n)


def get_models(model_path: str = None, embed_model_path: str = None, context_window: int = None,
			   max_new_tokens: int = None, load_in_8bit: bool = True):
	qwen_path = '/root/autodl-tmp/Qwen2-7B-Instruct'
	embedding_path = '/root/autodl-tmp/bge-large-zh-v1.5'

	model_path = model_path or qwen_path
	embed_model_path = embed_model_path or embedding_path
	context_window = context_window or 16000
	max_new_tokens = max_new_tokens or 1024

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
		generate_kwargs={"temperature": 0.01, "top_k": 4, "top_p": 0.95},
		device_map="cuda",
		messages_to_prompt=messages_to_prompt,
		completion_to_prompt=completion_to_prompt,
		model_kwargs=model_kwargs
	)
	embed_model = HuggingFaceEmbedding(model_name=embed_model_path)
	return llm, embed_model
