from llama_index.core.prompts.base import PromptTemplate
from llama_index.core.llms import LLM


def condition_analyze(
	llm: LLM,
	prompt: PromptTemplate,
	condition_true_word: str,
	**kwargs,
) -> bool:
	r"""
	Choose from two conditions according to the input.

	Args:
		llm (LLM): The used LLM.
		prompt (PromptTemplate): The prompt template.
		condition_true_word (str): The word that the LLM is supposed to output in the True condition.
		**kwargs:

	Returns:
		bool: True condition or False.
	"""
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
	r"""
	Asynchronously choose from two conditions according to the input.

	Args:
		llm (LLM): The used LLM.
		prompt (PromptTemplate): The prompt template.
		condition_true_word (str): The word that the LLM is supposed to output in the True condition.
		**kwargs:

	Returns:
		bool: True condition or False.
	"""
	llm_response = await llm.apredict(
		prompt=prompt,
		**kwargs,
	)

	llm_str = filter(lambda x: x.isalpha(), [char for char in llm_response])
	llm_str = "".join(llm_str)
	return llm_str == condition_true_word
