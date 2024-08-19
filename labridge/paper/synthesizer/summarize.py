import math
import asyncio

from llama_index.core import Settings
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.llms import LLM
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.base.response.schema import Response
from llama_index.core.response_synthesizers import get_response_synthesizer, ResponseMode, BaseSynthesizer

from llama_index.core.response_synthesizers.tree_summarize import TreeSummarize
from llama_index.core.types import RESPONSE_TEXT_TYPE
from llama_index.core.schema import BaseNode, MetadataMode
from llama_index.core.base.response.schema import RESPONSE_TYPE
from llama_index.core.utils import get_tokenizer
from llama_index.core import global_tokenizer
from llama_index.core.prompts.mixin import PromptDictType
from llama_index.core.prompts.default_prompt_selectors import DEFAULT_TREE_SUMMARIZE_PROMPT_SEL

from typing import List, Tuple, Sequence, Any

from labridge.paper.parse.parsers.base import MAINTEXT, METHODS
from labridge.paper.prompt.synthesize.paper_summarize import (
	PAPER_SUMMARIZE_QUERY,
	METHODS_SUMMARIZE_QUERY,
	PAPER_SECONDARY_SUMMARIZE_QUERY,
	METHODS_SECONDARY_SUMMARIZE_QUERY,
)


SUMMARIZE_MAX_TOKENS = 10000
SUMMARIZE_OVERLAP_CHUNK_NUM = 2


class PaperBatchSummarize(BaseSynthesizer):
	def __init__(
		self,
		llm: LLM = None,
		max_tokens: int = SUMMARIZE_MAX_TOKENS,
		overlap_chunk_num: int = SUMMARIZE_OVERLAP_CHUNK_NUM,
		summary_query: str = PAPER_SUMMARIZE_QUERY,
		secondary_query: str = PAPER_SECONDARY_SUMMARIZE_QUERY,
	):
		super().__init__(llm=llm)
		self._summary_template = DEFAULT_TREE_SUMMARIZE_PROMPT_SEL
		self._synthesizer = get_response_synthesizer(
			llm=self._llm,
			response_mode=ResponseMode.TREE_SUMMARIZE,
		)
		self._tokenizer = global_tokenizer or get_tokenizer()
		self._max_tokens = max_tokens
		self._overlap_chunk_num = overlap_chunk_num
		self._summary_query = summary_query
		self._secondary_query = secondary_query


	@property
	def summary_query(self) -> str:
		return self._summary_query

	@summary_query.setter
	def summary_query(self, value: str):
		self._summary_query = value

	@property
	def secondary_query(self) -> str:
		return self._secondary_query

	@secondary_query.setter
	def secondary_query(self, value: str):
		self._secondary_query = value

	def _get_prompts(self) -> PromptDictType:
		"""Get prompts."""
		return {"summary_template": self._summary_template}

	def _update_prompts(self, prompts: PromptDictType) -> None:
		"""Update prompts."""
		if "summary_template" in prompts:
			self._summary_template = prompts["summary_template"]

	def _calculate_batch_size(self, text_chunks: Sequence[str]) -> Tuple[bool, int]:
		token_num, max_node_tokens = 0, 0
		batch_mode = False
		for chunk in text_chunks:
			tokens = len(
				self._tokenizer(chunk)
			)
			token_num += tokens
			max_node_tokens = max(tokens, max_node_tokens)

		if token_num < self._max_tokens:
			return batch_mode, 0

		batch_mode = True
		batch_size = self._max_tokens // max_node_tokens
		return batch_mode, batch_size

	def batch_chunks(self, text_chunks: Sequence[str], batch_size: int):
		n = len(text_chunks)
		for start in range(0, n, batch_size - self._overlap_chunk_num):
			yield text_chunks[start: start + batch_size]

	def batch_get_response(self, batch_chunks: Sequence[str], query_str: str) -> RESPONSE_TEXT_TYPE:
		summary_template = self._summary_template.partial_format(query_str=query_str)
		response = self._llm.predict(
			summary_template,
			context_str="\n".join(batch_chunks),
		)
		return response

	async def abatch_get_response(self, batch_chunks: Sequence[str], query_str: str) -> RESPONSE_TEXT_TYPE:
		summary_template = self._summary_template.partial_format(query_str=query_str)
		response = await self._llm.apredict(
			summary_template,
			context_str="\n".join(batch_chunks),
		)
		return response

	def get_response(
        self,
        query_str: str,
        text_chunks: Sequence[str],
        **response_kwargs: Any,
    ) -> RESPONSE_TEXT_TYPE:
		batch_mode, batch_size = self._calculate_batch_size(text_chunks=text_chunks)

		print("summary batch size: ", batch_size)
		if not batch_mode:
			return self.batch_get_response(
				batch_chunks=text_chunks,
				query_str=self.summary_query,
			)

		summary_texts = []
		for chunks in self.batch_chunks(text_chunks=text_chunks, batch_size=batch_size):
			response = self.batch_get_response(
				batch_chunks=chunks,
				query_str=self.summary_query
			)
			summary_texts.append(response)

		final_response = self.batch_get_response(
			batch_chunks=summary_texts,
			query_str=self.secondary_query,
		)
		return final_response

	async def aget_response(
        self,
        query_str: str,
        text_chunks: Sequence[str],
        **response_kwargs: Any,
    ) -> RESPONSE_TEXT_TYPE:
		batch_mode, batch_size = self._calculate_batch_size(text_chunks=text_chunks)
		if not batch_mode:
			return await self.abatch_get_response(
				batch_chunks=text_chunks,
				query_str=self.summary_query,
			)

		tasks = [
			self.abatch_get_response(
				batch_chunks=batch_chunks,
				query_str=self.summary_query,
			) for batch_chunks in self.batch_chunks(text_chunks=text_chunks, batch_size=batch_size)
		]

		summary_texts = await asyncio.gather(*tasks)

		final_response = self.batch_get_response(
			batch_chunks=summary_texts,
			query_str=self.secondary_query,
		)
		return final_response


if __name__ == "__main__":
	import time
	from labridge.llm.models import get_models
	from llama_index.core.readers import SimpleDirectoryReader
	from llama_index.core.ingestion.pipeline import run_transformations
	from llama_index.core.ingestion.transformations import SentenceSplitter

	llm, embed_model = get_models()

	pp = PaperBatchSummarize(llm=llm)

	paper_path = "/root/zhisan/Labridge/docs/tmp_papers/杨再正/TorchProbe: Fuzzing Dynamic Deep Learning Compilers.pdf"
	reader = SimpleDirectoryReader(input_files=[paper_path])
	docs = reader.load_data()

	nodes = run_transformations(
		docs,
		[SentenceSplitter(chunk_size=1024, chunk_overlap=256, include_metadata=True), ]
	)

	# start = time.time()
	# summary = pp.synthesize(query="", nodes=[NodeWithScore(node=n) for n in nodes])
	# print(summary)
	# end = time.time()
	# print("common time: ", end - start)

	async def main():
		summary = await pp.asynthesize(query="", nodes=[NodeWithScore(node=n) for n in nodes])
		print(summary)

	start = time.time()
	asyncio.run(main())
	end = time.time()
	print("async time: ", end - start)
