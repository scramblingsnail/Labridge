import torch
import yaml

from pathlib import Path
from llama_index.llms.huggingface import HuggingFaceLLM
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.core.postprocessor import SentenceTransformerRerank
from transformers.utils.quantization_config import BitsAndBytesConfig

from .local.mindspore_models import MindsporeLLM, MindsporeEmbedding


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


def load_model_config():
	root = Path(__file__)
	for idx in range(3):
		root = root.parent

	cfg_path = str(root / "model_cfg.yaml")

	with open(cfg_path, 'r') as f:
		config = yaml.safe_load(f)
	return config


def get_models(
	model_path: str = None,
	embed_model_path: str = None,
	context_window: int = None,
	max_new_tokens: int = None,
	load_in_8bit: bool = True,
):
	config = load_model_config()
	backend = config.get("backend", "pytorch")
	model_path = model_path or config.get("llm_name")
	embed_model_path = embed_model_path or config.get("embedding_name")

	context_window = context_window or config.get("context_window")
	max_new_tokens = max_new_tokens or config.get("max_new_tokens")

	if backend.lower() == "mindspore":
		llm = MindsporeLLM(model_name=model_path)
		embed_model = MindsporeEmbedding(model_name=embed_model_path)
		return llm, embed_model

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
