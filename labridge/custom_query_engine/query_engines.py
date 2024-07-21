from llama_index.core.query_engine import BaseQueryEngine
from llama_index.core.settings import Settings
from llama_index.core.schema import QueryBundle
from llama_index.core.base.response.schema import RESPONSE_TYPE
from llama_index.core.llms import LLM
from llama_index.core.base.response.schema import Response

from typing import Union, Dict, Any


class SingleQueryEngine(BaseQueryEngine):
	def __init__(self, llm: LLM, prompt_tmpl: str):
		if llm is not None:
			self.llm = llm
		else:
			self.llm = Settings.llm
		self.prompt_tmpl = prompt_tmpl
		super().__init__(callback_manager=None)

	def _query(self, query_bundle: QueryBundle) -> RESPONSE_TYPE:
		return self.single_query(query_bundle.query_str)

	async def _aquery(self, query_bundle: QueryBundle) -> RESPONSE_TYPE:
		return self.single_query(query_bundle.query_str)

	def _get_prompt_modules(self) -> Dict[str, Any]:
		"""Get prompts."""
		return {}

	def single_query(self, query_str: str) -> Union[RESPONSE_TYPE, str]:
		query = self.prompt_tmpl.format(query_str)
		motivation_str = self.llm.complete(prompt=query)
		motivation = Response(motivation_str.text)
		return motivation
