import json
import llama_index.core.instrumentation as instrument

from llama_index.core.response_synthesizers.tree_summarize import TreeSummarize
from llama_index.core.postprocessor.sbert_rerank import BaseNodePostprocessor
from llama_index.core.question_gen.llm_generators import LLMQuestionGenerator
from llama_index.core.callbacks.schema import CBEventType, EventPayload
from llama_index.core.question_gen.types import BaseQuestionGenerator
from llama_index.core.response_synthesizers import BaseSynthesizer
from llama_index.core.base.response.schema import RESPONSE_TYPE
from llama_index.core.tools.query_engine import QueryEngineTool
from llama_index.core.schema import (
	QueryBundle,
	NodeWithScore,
)
from llama_index.core.llms import LLM
from llama_index.core.query_engine import (
    RetrieverQueryEngine,
    SubQuestionQueryEngine,
)

from typing import Optional, List

from ..prompt.synthesize.synthesize import PAPER_TREE_SUMMARIZE_PROMPT_SEL
from ..retrieve.paper_retriever import PaperRetriever
from ..parse.extractors.metadata_extract import (
	PAPER_POSSESSOR,
	PAPER_TITLE,
)


dispatcher = instrument.get_dispatcher(__name__)


PAPER_QUERY_TOOL_NAME = "Paper_query_tool"
PAPER_QUERY_TOOL_DESCRIPTION = (
	"This tool will answer academic questions with the help of abundant research papers, "
	"you can use the output of this tool as response directly, without extra modifications."
)

PAPER_SUB_QUERY_TOOL_NAME = "Paper_sub_queries_tool"
PAPER_SUB_QUERY_TOOL_DESCRIPTION = (
	"This tool help you to answer the query with the access to abundant research papers.\n"
	"IN ADDITION, This tool helps you to decompose the complex query into several sub-queries, "
	"then utilize the information in these research papers to answer these sub-queries,"
	"finally merge these information to obtain the answer of the complex raw query.\n"
	"When answering COMPLEX academic queries, use this tool to make your answer logical, comprehensive and professional."
	"Similarly,The obtained results of this tool are often conclusive and concise, without enough detailed information."
	"When answering academic queries, use this tool to make your answer accurate, professional, and convincing."
)

class PaperQueryEngine(RetrieverQueryEngine):
	r"""
	TODO: Docstring
	"""
	def __init__(
		self,
		llm: LLM,
		paper_retriever: PaperRetriever,
		re_ranker: BaseNodePostprocessor = None,
		verbose: bool = False
	):
		response_synthesizer = TreeSummarize(
			llm=llm,
			callback_manager=paper_retriever.callback_manager,
			summary_template=PAPER_TREE_SUMMARIZE_PROMPT_SEL,
			verbose=verbose,)
		if re_ranker is None:
			postprocessors = []
		else:
			postprocessors = [re_ranker, ]
		self.retrieved_nodes = None
		super().__init__(retriever=paper_retriever,
						 node_postprocessors=postprocessors,
						 response_synthesizer=response_synthesizer)

	def get_ref_info(self) -> List[str]:
		doc_ids, doc_titles, doc_possessors = [], [], []
		for node_score in self.retrieved_nodes:
			ref_doc_id = node_score.node.ref_doc_id
			if ref_doc_id not in doc_ids:
				doc_ids.append(ref_doc_id)
				title = node_score.node.metadata.get(PAPER_TITLE) or ref_doc_id
				possessor = node_score.node.metadata.get(PAPER_POSSESSOR)
				doc_titles.append(title)
				doc_possessors.append(possessor)

		references = []
		for doc_idx in range(len(doc_titles)):
			ref_str = f"**REFERENCE:**:\n"
			ref_str += f"\t**Title:** {doc_titles[doc_idx]}\n"
			ref_str += f"\t**Possessor:** {doc_possessors[doc_idx]}\n"
			references.append(ref_str)
		return references

	@dispatcher.span
	def _query(self, query_bundle: QueryBundle) -> RESPONSE_TYPE:
		"""Answer a query, and add references """
		with self.callback_manager.event(CBEventType.QUERY,
				payload={EventPayload.QUERY_STR: query_bundle.query_str}) as query_event:
			nodes = self.retrieve(query_bundle)
			self.retrieved_nodes = nodes
			response = self._response_synthesizer.synthesize(query=query_bundle, nodes=nodes, )
			query_event.on_end(payload={EventPayload.RESPONSE: response})
		return response

	@dispatcher.span
	async def _aquery(self, query_bundle: QueryBundle) -> RESPONSE_TYPE:
		"""Answer a query."""
		with self.callback_manager.event(CBEventType.QUERY,
				payload={EventPayload.QUERY_STR: query_bundle.query_str}) as query_event:
			nodes = await self.aretrieve(query_bundle)
			response = await self._response_synthesizer.asynthesize(query=query_bundle, nodes=nodes, )
			query_event.on_end(payload={EventPayload.RESPONSE: response})
		return response

class PaperSubQueryEngine(SubQuestionQueryEngine):
	def __init__(self,
				 llm: LLM,
				 paper_query_engine: PaperQueryEngine,
				 question_gen: Optional[BaseQuestionGenerator] = None,
				 response_synthesizer: Optional[BaseSynthesizer] = None,
				 verbose: bool = True,
				 use_async: bool = True, ):
		paper_query_tool = QueryEngineTool.from_defaults(
			query_engine=paper_query_engine,
			name=PAPER_QUERY_TOOL_NAME,
			description=PAPER_QUERY_TOOL_DESCRIPTION)
		callback_manager = paper_query_engine.callback_manager
		if question_gen is None:
			try:
				from llama_index.question_gen.openai import (OpenAIQuestionGenerator, )  # pants: no-infer-dep

				# try to use OpenAI function calling based question generator.
				# if incompatible, use general LLM question generator
				question_gen = OpenAIQuestionGenerator.from_defaults(llm=llm)

			except ImportError as e:
				raise ImportError("`llama-index-question-gen-openai` package cannot be found. "
								  "Please install it by using `pip install `llama-index-question-gen-openai`")
			except ValueError:
				question_gen = LLMQuestionGenerator.from_defaults(llm=llm)

			response_synthesizer = TreeSummarize(
				llm=llm,
				callback_manager=callback_manager,
				summary_template=PAPER_TREE_SUMMARIZE_PROMPT_SEL,
				verbose=verbose,
				use_async=use_async
			)

		super().__init__(
			question_gen=question_gen,
			response_synthesizer=response_synthesizer,
			query_engine_tools=[paper_query_tool],
			callback_manager=callback_manager,
			verbose=verbose,
			use_async=use_async,
		)
