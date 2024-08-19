from llama_index.core.prompts.base import PromptTemplate
from llama_index.core.llms import LLM


def condition_analyze(
	llm: LLM,
	prompt: PromptTemplate,
	condition_true_word: str,
	**kwargs,
) -> bool:
	llm_response = llm.predict(
		prompt=prompt,
		**kwargs,
	)

	llm_str = filter(lambda x: x.isalpha(), [char for char in llm_response])
	llm_str = "".join(llm_str)
	return llm_str.lower() == condition_true_word.lower()

async def acondition_analyze(
	llm: LLM,
	prompt: PromptTemplate,
	condition_true_word: str,
	**kwargs,
) -> bool:
	llm_response = await llm.apredict(
		prompt=prompt,
		**kwargs,
	)

	llm_str = filter(lambda x: x.isalpha(), [char for char in llm_response])
	llm_str = "".join(llm_str)
	return llm_str == condition_true_word
