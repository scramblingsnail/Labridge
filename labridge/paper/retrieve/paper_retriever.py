from pathlib import Path
from typing import List, Optional, Union, Callable, Tuple

from llama_index.core.indices.document_summary.retrievers import DocumentSummaryIndexEmbeddingRetriever
from llama_index.core.indices.document_summary.base import DocumentSummaryRetrieverMode
from llama_index.core.service_context import ServiceContext
from llama_index.core.prompts import BasePromptTemplate
from llama_index.core.storage import StorageContext
from llama_index.core.llms import LLM
from llama_index.core.schema import (
	NodeWithScore,
	BaseNode,
)
from llama_index.core import (
	VectorStoreIndex,
	load_index_from_storage,
	QueryBundle,
)
from llama_index.core.settings import (
	Settings,
	llm_from_settings_or_context,
)
from llama_index.core.retrievers import (
	BaseRetriever,
	VectorIndexRetriever,
)
from llama_index.core.indices.utils import (
    default_format_node_batch_fn,
    default_parse_choice_select_answer_fn,
)

from ...common.prompt.llm_doc_choice_select import DOC_CHOICE_SELECT_PROMPT
from ..store.paper_store import (
	DEFAULT_PAPER_VECTOR_PERSIST_DIR,
	DEFAULT_PAPER_SUMMARY_PERSIST_DIR,
	PAPER_VECTOR_INDEX_ID,
	PAPER_SUMMARY_INDEX_ID,
)


class PaperSummaryLLMPostSelector:
	r"""
	Use LLM to re-rank the retrieved papers obtained by vector_retriever and summary_retriever,
	according to their summaries.
	"""
	def __init__(
		self,
		summary_nodes: List[BaseNode],
		llm: Optional[LLM] = None,
		choice_select_prompt: Optional[BasePromptTemplate] = None,
		choice_batch_size: int = 10,
		choice_top_k: int = 2,
		format_node_batch_fn: Optional[Callable] = None,
		parse_choice_select_answer_fn: Optional[Callable] = None,
	):
		self._summary_nodes = summary_nodes
		self._choice_select_prompt = (choice_select_prompt or DOC_CHOICE_SELECT_PROMPT)
		self._choice_batch_size = choice_batch_size
		self._choice_top_k = choice_top_k
		self._format_node_batch_fn = (format_node_batch_fn or default_format_node_batch_fn)
		self._parse_choice_select_answer_fn = (parse_choice_select_answer_fn or default_parse_choice_select_answer_fn)
		self._llm = llm or Settings.llm

	def select(
		self,
		query_bundle: QueryBundle
	) -> List[str]:
		r"""
		Return the ref_doc_ids, titles, possessors of the selected docs.
		"""
		all_nodes: List[BaseNode] = []
		all_relevances: List[float] = []
		for idx in range(0, len(self._summary_nodes), self._choice_batch_size):
			summary_nodes = self._summary_nodes[idx: idx + self._choice_batch_size]
			query_str = query_bundle.query_str
			fmt_batch_str = self._format_node_batch_fn(summary_nodes)
			# call each batch independently
			raw_response = self._llm.predict(
				self._choice_select_prompt,
				context_str=fmt_batch_str,
				query_str=query_str,
			)
			raw_choices, relevances = self._parse_choice_select_answer_fn(raw_response, len(summary_nodes))
			choice_idxs = [choice - 1 for choice in raw_choices]

			choice_summary_nodes = [summary_nodes[ci] for ci in choice_idxs]

			all_nodes.extend(choice_summary_nodes)
			all_relevances.extend(relevances)

		zipped_list = list(zip(all_nodes, all_relevances))
		sorted_list = sorted(zipped_list, key=lambda x: x[1], reverse=True)
		top_k_list = sorted_list[: self._choice_top_k]

		doc_ids = [node.ref_doc_id for node, relevance in top_k_list]
		return doc_ids


class PaperRetriever(BaseRetriever):
	r"""
	We use hybrid, multi-level retrieving methods.

	In the first step, the retriever retrieve the vector index and the summary index to get candidate papers.
	These two index storages are constructed in the class `PaperStorage`, refer to its docstring for details.

	- In the vector index, the paper contents except for references are chunked and embedded. The retriever get
	`vector_similarity_top_k` most relevant text chunk from the vector index, then we collect their `ref_doc_id`.
	- In the summary index, each paper is summarized. Both the summary text and the paper chunks are stored.
	The retriever search in the summary texts to get `summary_similarity_top_k` most relevant summaries of docs.
	Similarly, we collect their `doc_id`.

	We have collected several relevant papers in the first step. Subsequently, we use the `PaperSummaryLLMPostSelector`
	to rank these papers according to the relevance between their summaries and the query, the relevance scores are
	given by the LLM. Among these papers, the LLM selects `docs_top_k` most relevant papers.

	Finally, we conduct secondary_retrieve among the text chunks of these luckily selected papers.
	Note that, in this period, we hide all metadata of these nodes from the LLM and the embed model for the sake of
	grained retrieving. At last, we will get `re_retrieve_top_k` text chunks.

	If the `final_use_context` is set to True, the prev_node and next_node of each node will be added.
	If the `final_use_summary` is set to True, the summary_node corresponding to each_node's doc will be added.

	Args:
		llm (LLM): the employed LLM.
		paper_vector_retriever (VectorIndexRetriever): the retriever based on the VectorIndex in paper storage.
		paper_summary_retriever (DocumentSummaryIndexEmbeddingRetriever):
			the retriever based on the DocumentSummaryIndex in the paper storage.
		docs_top_k (int): the number of most relevant docs in the second retrieving step.
		re_retrieve_top_k (int): the number of the finally retrieved nodes.
		final_use_context (bool): Whether to add the context nodes of each final node.
		final_use_summary (bool): Whether to add the summary node of each final node's doc.
	"""
	def __init__(
		self,
		llm: LLM,
		paper_vector_retriever: VectorIndexRetriever,
		paper_summary_retriever: DocumentSummaryIndexEmbeddingRetriever,
		docs_top_k: int = 2,
		re_retrieve_top_k: int = 5,
		final_use_context: bool = True,
		final_use_summary: bool = True
	):
		self.paper_vector_retriever = paper_vector_retriever
		self.paper_summary_retriever = paper_summary_retriever
		self.paper_summary_post_selector = PaperSummaryLLMPostSelector(
			summary_nodes=[],
			llm=llm,
			choice_top_k=docs_top_k,
		)
		self.re_retrieve_top_k = re_retrieve_top_k
		self.final_use_context = final_use_context
		self.final_use_summary = final_use_summary
		self.doc_id_to_summary_id = self.paper_summary_retriever._index._index_struct.doc_id_to_summary_id
		self.summary_id_to_node_ids = self.paper_summary_retriever._index._index_struct.summary_id_to_node_ids
		super().__init__()

	def _exclude_all_llm_metadata(self, node: BaseNode):
		r""" Hidden all metadata of a node to LLM. """
		node.excluded_llm_metadata_keys.extend(list(node.metadata.keys()))

	def _exclude_all_embedding_metadata(self, node: BaseNode):
		r""" Hidden all metadata of a node to the embed model. """
		node.excluded_embed_metadata_keys.extend(list(node.metadata.keys()))

	def _secondary_retrieve(
		self,
		final_doc_ids: List[str],
		query_bundle: QueryBundle
	) -> Tuple[List[NodeWithScore], List[NodeWithScore]]:
		r"""
		Secondary retrieve among the nodes of the selected papers.

		Args:
			final_doc_ids (List[str]): the doc_ids of the selected papers.
			query_bundle (QueryBundle): the query bundle.

		Returns:
			the summary_nodes and the content_nodes:

				- summary_nodes (List[NodeWithScore]): the summary nodes of these docs.
				- content_nodes (List[NodeWithScore]): the retrieved nodes among the chunked nodes of these docs.
		"""
		# get all nodes of these docs.
		summary_nodes = []
		all_doc_nodes = []
		for doc_id in final_doc_ids:
			summary_id = self.doc_id_to_summary_id[doc_id]
			summary_node = self.paper_summary_retriever._index.docstore.get_node(summary_id)
			# exclude metadata of summary nodes for llm using.
			self._exclude_all_llm_metadata(summary_node)
			summary_nodes.append(NodeWithScore(node=summary_node))

			# all doc nodes.
			doc_node_ids = self.summary_id_to_node_ids[summary_id]
			doc_nodes = self.paper_summary_retriever._index.docstore.get_nodes(doc_node_ids)
			# exclude metadata of content nodes
			for doc_node in doc_nodes:
				self._exclude_all_llm_metadata(doc_node)
				self._exclude_all_embedding_metadata(doc_node)
			all_doc_nodes.extend(doc_nodes)

		content_index = VectorStoreIndex(nodes=all_doc_nodes, embed_model=self.paper_vector_retriever._embed_model)
		content_retriever = content_index.as_retriever(similarity_top_k=self.re_retrieve_top_k)
		content_nodes = content_retriever.retrieve(query_bundle)
		return summary_nodes, content_nodes

	def _get_context(self, content_nodes: List[NodeWithScore]) -> List[NodeWithScore]:
		r"""
		Get the 1-hop context nodes of each content node retrieved in the secondary retrieving.
		"""
		content_ids = [node.node.node_id for node in content_nodes]
		extra_ids = []
		for node in content_nodes:
			prev_node = node.node.prev_node
			next_node = node.node.next_node
			if prev_node is not None:
				prev_id = node.node.prev_node.node_id
				if prev_id not in content_ids:
					extra_ids.append(prev_id)
					content_ids.append(prev_id)

			if next_node is not None:
				next_id = node.node.next_node.node_id
				if next_id not in content_ids:
					extra_ids.append(next_id)
					content_ids.append(next_id)

		context_nodes = self.paper_summary_retriever._index.docstore.get_nodes(extra_ids)
		context_nodes = [NodeWithScore(node=node) for node in context_nodes]
		# exclude metadata in LLM using.
		for node in context_nodes:
			self._exclude_all_llm_metadata(node.node)
		return context_nodes

	def _retrieve(
		self,
		query_bundle: QueryBundle,
	) -> List[NodeWithScore]:
		r""" Retrieve """
		vector_nodes = self.paper_vector_retriever.retrieve(query_bundle)
		summary_chunk_nodes = self.paper_summary_retriever.retrieve(query_bundle)

		hybrid_doc_ids = set()
		for node in summary_chunk_nodes + vector_nodes:
			hybrid_doc_ids.add(node.node.ref_doc_id)

		doc_id_to_summary_id = self.paper_summary_retriever._index._index_struct.doc_id_to_summary_id
		hybrid_summary_ids = [doc_id_to_summary_id[doc_id] for doc_id in hybrid_doc_ids]
		doc_summary_nodes = self.paper_summary_retriever._index.docstore.get_nodes(hybrid_summary_ids)

		self.paper_summary_post_selector._summary_nodes = doc_summary_nodes
		final_doc_ids = self.paper_summary_post_selector.select(query_bundle)

		summary_nodes, content_nodes = self._secondary_retrieve(
			final_doc_ids=final_doc_ids,
			query_bundle=query_bundle,
		)

		final_nodes = content_nodes
		if self.final_use_summary:
			final_nodes.extend(summary_nodes)

		if self.final_use_context:
			context_nodes = self._get_context(content_nodes)
			final_nodes.extend(context_nodes)

		return final_nodes

	@classmethod
	def from_storage(
		cls,
		llm: Optional[LLM] = None,
		vector_persist_dir: Optional[Union[Path, str]] = None,
		paper_summary_persist_dir: Optional[Union[Path, str]] = None,
		vector_similarity_top_k: Optional[int] = 10,
		summary_similarity_top_k: Optional[int] = 3,
		service_context: Optional[ServiceContext] = None,
		docs_top_k: int = 2,
		re_retrieve_top_k: int = 4,
		final_use_context: bool = True,
		final_use_summary: bool = True,
	):
		root = Path(__file__)
		for i in range(4):
			root = root.parent

		llm = llm or llm_from_settings_or_context(Settings, service_context)

		vector_persist_dir = vector_persist_dir or root / DEFAULT_PAPER_VECTOR_PERSIST_DIR
		vector_storage_context = StorageContext.from_defaults(persist_dir=vector_persist_dir)
		vector_index = load_index_from_storage(
			storage_context=vector_storage_context,
			index_id=PAPER_VECTOR_INDEX_ID,
			service_context=service_context)
		vector_retriever = vector_index.as_retriever(similarity_top_k=vector_similarity_top_k)

		paper_summary_persist_dir = paper_summary_persist_dir or root / DEFAULT_PAPER_SUMMARY_PERSIST_DIR
		paper_summary_storage_context = StorageContext.from_defaults(persist_dir=paper_summary_persist_dir)
		paper_summary_index = load_index_from_storage(
			storage_context=paper_summary_storage_context,
			index_id=PAPER_SUMMARY_INDEX_ID,
			service_context=service_context)
		summary_retriever = paper_summary_index.as_retriever(
			retriever_mode=DocumentSummaryRetrieverMode.EMBEDDING,
			similarity_top_k=summary_similarity_top_k)
		return cls(
			llm = llm,
			paper_vector_retriever=vector_retriever,
			paper_summary_retriever=summary_retriever,
			docs_top_k=docs_top_k,
			re_retrieve_top_k=re_retrieve_top_k,
			final_use_context=final_use_context,
			final_use_summary=final_use_summary,
		)
