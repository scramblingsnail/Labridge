from llama_index.core.embeddings import BaseEmbedding
from llama_index.core import Settings
import llama_index.core.instrumentation as instrument
import fsspec
from llama_index.core.schema import NodeWithScore
from llama_index.core.llms import LLM
from llama_index.core.indices.vector_store.retrievers.retriever import VectorIndexRetriever
from llama_index.core.vector_stores.types import FilterOperator
from llama_index.core.vector_stores.types import (
	MetadataFilters,
	MetadataFilter,
)
from pathlib import Path
from typing import List, Optional, Union, Callable, Tuple, Dict

import llama_index.core.instrumentation as instrument
from llama_index.core.schema import MetadataMode
from llama_index.core.indices.document_summary.retrievers import DocumentSummaryIndexEmbeddingRetriever
from llama_index.core.indices.document_summary.base import DocumentSummaryRetrieverMode
from llama_index.core.service_context import ServiceContext
from llama_index.core.prompts import BasePromptTemplate
from llama_index.core.storage import StorageContext
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.llms import LLM
from llama_index.core.schema import (
	NodeWithScore,
	BaseNode,
	TextNode,
)
from llama_index.core import (
	VectorStoreIndex,
	load_index_from_storage,
)
from llama_index.core.settings import (
	Settings,
	llm_from_settings_or_context,
	embed_model_from_settings_or_context,
)
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.indices.utils import (
    default_format_node_batch_fn,
    default_parse_choice_select_answer_fn,
)

from labridge.common.utils.time import parse_date_list
from labridge.common.prompt.llm_doc_choice_select import DOC_CHOICE_SELECT_PROMPT
from labridge.func_modules.paper.store.shared_paper_store import SharedPaperStorage
from labridge.func_modules.paper.store.temporary_store import (
	RecentPaperStore,
	TMP_PAPER_DATE,
	TMP_PAPER_NODE_TYPE_KEY,
	TMP_PAPER_DOC_NODE_TYPE,
)
from labridge.accounts.users import AccountManager
from labridge.func_modules.paper.parse.extractors.metadata_extract import (
	PAPER_POSSESSOR,
	PAPER_ABSTRACT,
	PAPER_TITLE,
	PAPER_REL_FILE_PATH,
)
from labridge.func_modules.paper.store.shared_paper_store import (
	SharedPaperNodeType,
	SHARED_PAPER_NODE_TYPE,
	SHARED_PAPER_VECTOR_INDEX_PERSIST_DIR,
	SHARED_PAPER_VECTOR_INDEX_ID,
	SHARED_PAPER_SUMMARY_KEY,
)


from typing import Any, List


PAPER_VECTOR_TOP_K = 10
PAPER_TOP_K = 2
PAPER_RETRIEVE_TOP_K = 3


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
		choice_top_k: int = PAPER_TOP_K,
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

	def format_batch_summaries(self, batch_summaries: List[str], ) -> str:
		"""
		Formatted batch summaries.
		"""
		fmt_node_txts = []
		for idx in range(len(batch_summaries)):
			number = idx + 1
			fmt_node_txts.append(
				f"Document {number}:\n"
				f"{batch_summaries[idx]}"
			)
		return "\n\n".join(fmt_node_txts)

	def select(
		self,
		item_to_be_retrieved: str,
		paper_summaries: Dict[str, str]
	) -> List[str]:
		r"""
		Select from the paper summaries according to the relevance to the retrieving string.

		Args:
			item_to_be_retrieved (str): The retrieving string.
			paper_summaries (Dict[str, str]): Key: paper_node_id, value: paper summary.

		Return the ref_doc_ids, titles, possessors of the selected docs.
		"""
		all_paper_ids: List[str] = []
		all_relevances: List[float] = []

		paper_ids = list(paper_summaries.keys())
		summaries = [paper_summaries[key] for key in paper_ids]
		max_try = 3

		for idx in range(0, len(summaries), self._choice_batch_size):
			batch_summaries = summaries[idx: idx + self._choice_batch_size]
			batch_paper_ids = paper_ids[idx: idx + self._choice_batch_size]
			fmt_batch_str = self.format_batch_summaries(batch_summaries=batch_summaries)
			# call each batch independently
			batch_done = False
			try_idx = 1
			while not batch_done and try_idx < max_try:
				try:
					try_idx += 1
					raw_response = self._llm.predict(
						self._choice_select_prompt,
						context_str=fmt_batch_str,
						query_str=item_to_be_retrieved,
					)
					raw_choices, relevances = self._parse_choice_select_answer_fn(raw_response, len(summaries))
					choice_idxs = [choice - 1 for choice in raw_choices]
					choice_ids = [batch_paper_ids[ci] for ci in choice_idxs]

					all_paper_ids.extend(choice_ids)
					all_relevances.extend(relevances)
					batch_done = True
				except:
					pass

		zipped_list = list(zip(all_paper_ids, all_relevances))
		sorted_list = sorted(zipped_list, key=lambda x: x[1], reverse=True)
		top_k_list = sorted_list[: self._choice_top_k]

		selected_paper_ids = [paper_id for paper_id, relevance in top_k_list]
		return selected_paper_ids

	async def aselect(
		self,
		item_to_be_retrieved: str,
		paper_summaries: Dict[str, str],
	) -> List[str]:
		r"""
		Asynchronously select from the paper summaries according to the relevance to the retrieving string.

		Args:
			item_to_be_retrieved (str): The retrieving string.
			paper_summaries (Dict[str, str]): Key: paper_node_id, value: paper summary.

		Return the ref_doc_ids, titles, possessors of the selected docs.
		"""
		all_paper_ids: List[str] = []
		all_relevances: List[float] = []

		paper_ids = list(paper_summaries.keys())
		summaries = [paper_summaries[key] for key in paper_ids]
		max_try = 3

		for idx in range(0, len(summaries), self._choice_batch_size):
			batch_summaries = summaries[idx: idx + self._choice_batch_size]
			batch_paper_ids = paper_ids[idx: idx + self._choice_batch_size]
			fmt_batch_str = self.format_batch_summaries(batch_summaries=batch_summaries)
			# call each batch independently
			batch_done = False
			try_idx = 1
			while not batch_done and try_idx < max_try:
				try:
					try_idx += 1
					raw_response = await self._llm.apredict(
						self._choice_select_prompt,
						context_str=fmt_batch_str,
						query_str=item_to_be_retrieved,
					)
					raw_choices, relevances = self._parse_choice_select_answer_fn(raw_response, len(summaries))
					choice_idxs = [choice - 1 for choice in raw_choices]
					choice_ids = [batch_paper_ids[ci] for ci in choice_idxs]

					all_paper_ids.extend(choice_ids)
					all_relevances.extend(relevances)
					batch_done = True
				except:
					pass

		zipped_list = list(zip(all_paper_ids, all_relevances))
		sorted_list = sorted(zipped_list, key=lambda x: x[1], reverse=True)
		top_k_list = sorted_list[: self._choice_top_k]

		selected_paper_ids = [paper_id for paper_id, relevance in top_k_list]
		return selected_paper_ids


class SharedPaperRetriever:

	def __init__(
		self,
		llm: LLM,
		embed_model: BaseEmbedding,
		shared_vector_index: VectorStoreIndex,
		vector_similarity_top_k: int = PAPER_VECTOR_TOP_K,
		papers_top_k: int = PAPER_TOP_K,
		re_retrieve_top_k: int = PAPER_RETRIEVE_TOP_K,
		final_use_context: bool = True,
		final_use_summary: bool = True,
	):
		self.paper_summary_post_selector = PaperSummaryLLMPostSelector(
			summary_nodes=[],
			llm=llm,
			choice_top_k=papers_top_k,
		)
		self.shared_vector_index = shared_vector_index
		self.shared_paper_retriever = shared_vector_index.as_retriever(similarity_top_k=vector_similarity_top_k)
		self.vector_similarity_top_k = vector_similarity_top_k
		self.re_retrieve_top_k = re_retrieve_top_k
		self.final_use_context = final_use_context
		self.final_use_summary = final_use_summary
		self._account_manager = AccountManager()
		root = Path(__file__)
		for i in range(5):
			root = root.parent
		self.root = root

	@classmethod
	def from_storage(
		cls,
		llm: Optional[LLM] = None,
		embed_model: Optional[BaseEmbedding] = None,
		vector_persist_dir: Optional[str] = None,
		vector_similarity_top_k: Optional[int] = PAPER_VECTOR_TOP_K,
		papers_top_k: int = PAPER_TOP_K,
		re_retrieve_top_k: int = PAPER_RETRIEVE_TOP_K,
		service_context: Optional[ServiceContext] = None,
		final_use_context: bool = True,
		final_use_summary: bool = True,
	):
		r"""
		Load from an existing storage.
		"""
		root = Path(__file__)
		for i in range(5):
			root = root.parent

		llm = llm or llm_from_settings_or_context(Settings, service_context)
		embed_model = embed_model or embed_model_from_settings_or_context(Settings, service_context)

		vector_persist_dir = vector_persist_dir or root / SHARED_PAPER_VECTOR_INDEX_PERSIST_DIR
		vector_storage_context = StorageContext.from_defaults(persist_dir=vector_persist_dir)
		shared_vector_index = load_index_from_storage(
			storage_context=vector_storage_context,
			index_id=SHARED_PAPER_VECTOR_INDEX_ID,
			embed_model=embed_model,
		)
		return cls(
			llm=llm,
			embed_model=embed_model,
			shared_vector_index=shared_vector_index,
			vector_similarity_top_k=vector_similarity_top_k,
			papers_top_k=papers_top_k,
			re_retrieve_top_k=re_retrieve_top_k,
			final_use_context=final_use_context,
			final_use_summary=final_use_summary,
		)

	@property
	def _chunk_node_filter(self) -> MetadataFilter:
		chunk_type_filter = MetadataFilter(
			key=SHARED_PAPER_NODE_TYPE,
			value=SharedPaperNodeType.PAPER_CHUNK,
			operator=FilterOperator.EQ,
		)
		return chunk_type_filter

	def _user_filter(self, user_id: str) -> MetadataFilter:
		self._account_manager.check_valid_user(user_id=user_id)
		user_id_filter = MetadataFilter(
			key=PAPER_POSSESSOR,
			value=user_id,
			operator=FilterOperator.EQ,
		)
		return user_id_filter

	def get_parent_summaries(self, chunk_nodes: List[NodeWithScore]) -> Optional[Dict[str, str]]:
		paper_ids = set()
		for node_score in chunk_nodes:
			paper_id = node_score.node.parent_node.node_id
			paper_ids.add(paper_id)

		paper_nodes = self.shared_vector_index.docstore.get_nodes(node_ids=list(paper_ids))
		paper_themes = {}
		for node in paper_nodes:
			theme = ""
			summary = node.metadata.get(SHARED_PAPER_SUMMARY_KEY, None)
			abstract = node.metadata.get(PAPER_ABSTRACT, None)
			if summary is None and abstract is None:
				continue

			if abstract:
				theme += f"Abstract:\n{abstract}\n"
			if summary:
				theme += f"Summary:\n{summary}\n"
			paper_themes[node.node_id] = theme

		if len(paper_themes.keys()) < 1:
			return None
		return paper_themes

	def _reset_retriever(self, target_user_id: str = None):
		filters = [self._chunk_node_filter, ]

		if target_user_id is not None:
			filters.append(self._user_filter(user_id=target_user_id))

		self.shared_paper_retriever._filters = MetadataFilters(filters=filters)
		self.shared_paper_retriever._similarity_top_k = self.vector_similarity_top_k

	def _add_summary_nodes(self, retrieved_nodes: List[NodeWithScore]) -> List[NodeWithScore]:
		paper_summaries = self.get_parent_summaries(chunk_nodes=retrieved_nodes)

		summary_nodes = []
		for paper_id in paper_summaries.keys():
			paper_node = self.shared_vector_index.docstore.get_node(node_id=paper_id)
			title = paper_node.metadata[PAPER_TITLE]
			summary = paper_summaries[paper_id]
			summary_node = TextNode(
				text=f"Title: {title}\n\nSummary:\n{summary}",
				metadata=paper_node.child_nodes[0].metadata,
			)
			self._exclude_all_llm_metadata([summary_node])
			self._exclude_all_embedding_metadata([summary_node])
			summary_nodes.append(NodeWithScore(node=summary_node))

		retrieved_nodes.extend(summary_nodes)
		return retrieved_nodes

	def _add_context(self, content_nodes: List[NodeWithScore]) -> List[NodeWithScore]:
		r"""
		Get the 1-hop context nodes of each content node retrieved in the secondary retrieving.
		"""
		content_ids = [node.node.node_id for node in content_nodes]
		new_ids = []
		for node in content_nodes:
			prev_node = node.node.prev_node
			next_node = node.node.next_node
			if prev_node is not None:
				prev_id = node.node.prev_node.node_id
				if prev_id not in content_ids:
					content_ids.append(prev_id)
					new_ids.append(prev_id)

			new_ids.append(node.node_id)

			if next_node is not None:
				next_id = node.node.next_node.node_id
				if next_id not in content_ids:
					content_ids.append(next_id)
					new_ids.append(next_id)

		context_nodes = self.shared_vector_index.docstore.get_nodes(new_ids)
		# exclude metadata in LLM using.
		self._exclude_all_llm_metadata(nodes=context_nodes)
		context_nodes = [NodeWithScore(node=node) for node in context_nodes]
		return context_nodes

	def _exclude_all_llm_metadata(self, nodes: List[BaseNode]):
		r""" Hidden all metadata of a node to LLM. """
		for node in nodes:
			node.excluded_llm_metadata_keys.extend(list(node.metadata.keys()))

	def _exclude_all_embedding_metadata(self, nodes: List[BaseNode]):
		r""" Hidden all metadata of a node to the embed model. """
		for node in nodes:
			node.excluded_embed_metadata_keys.extend(list(node.metadata.keys()))

	def secondary_retrieve(
		self,
		item_to_be_retrieved: str,
		paper_ids: List[str],
	) -> List[NodeWithScore]:
		node_ids = []
		for paper_id in paper_ids:
			paper_node = self.shared_vector_index.docstore.get_node(node_id=paper_id)
			chunk_ids = [node.node_id for node in paper_node.child_nodes]
			node_ids.extend(chunk_ids)

		chunk_nodes = self.shared_vector_index.docstore.get_nodes(node_ids=node_ids)
		self._exclude_all_llm_metadata(nodes=chunk_nodes)
		self._exclude_all_embedding_metadata(nodes=chunk_nodes)

		content_index = VectorStoreIndex(nodes=chunk_nodes, embed_model=self.shared_vector_index._embed_model)
		content_retriever = content_index.as_retriever(similarity_top_k=self.re_retrieve_top_k)
		retrieved_nodes = content_retriever.retrieve(item_to_be_retrieved)

		if self.final_use_context:
			retrieved_nodes = self._add_context(content_nodes=retrieved_nodes)
		if self.final_use_summary:
			retrieved_nodes = self._add_summary_nodes(retrieved_nodes=retrieved_nodes)
		return retrieved_nodes

	async def asecondary_retrieve(
		self,
		item_to_be_retrieved: str,
		paper_ids: List[str],
	) -> List[NodeWithScore]:
		node_ids = []
		for paper_id in paper_ids:
			paper_node = self.shared_vector_index.docstore.get_node(node_id=paper_id)
			chunk_ids = [node.node_id for node in paper_node.child_nodes]
			node_ids.extend(chunk_ids)

		chunk_nodes = self.shared_vector_index.docstore.get_nodes(node_ids=node_ids)
		self._exclude_all_llm_metadata(nodes=chunk_nodes)
		self._exclude_all_embedding_metadata(nodes=chunk_nodes)

		content_index = VectorStoreIndex(nodes=chunk_nodes, embed_model=self.shared_vector_index._embed_model)
		content_retriever = content_index.as_retriever(similarity_top_k=self.re_retrieve_top_k)
		retrieved_nodes = await content_retriever.aretrieve(item_to_be_retrieved)

		if self.final_use_context:
			retrieved_nodes = self._add_context(content_nodes=retrieved_nodes)
		if self.final_use_summary:
			retrieved_nodes = self._add_summary_nodes(retrieved_nodes=retrieved_nodes)
		return retrieved_nodes

	def retrieve(
		self,
		item_to_be_retrieved: str,
		target_user_id: str = None,
	) -> List[NodeWithScore]:
		r"""
		This tool is used to retrieve academic information in the Laboratory's shared paper database.
		It is useful to help answer the user's academic questions.

		Args:
			item_to_be_retrieved (str): The things that you want to retrieve in the shared paper database.
			target_user_id (str): If given, the retrieval range will be confined to the papers belonging to the given user.
				Defaults to None.
		"""
		# This docstring is used as the tool description.
		self._reset_retriever(target_user_id=target_user_id)
		chunk_nodes = self.shared_paper_retriever.retrieve(item_to_be_retrieved)
		paper_summaries = self.get_parent_summaries(chunk_nodes=chunk_nodes)
		if paper_summaries is None:
			return []

		final_paper_ids = self.paper_summary_post_selector.select(
			item_to_be_retrieved=item_to_be_retrieved,
			paper_summaries=paper_summaries,
		)

		retrieved_nodes = self.secondary_retrieve(
			item_to_be_retrieved=item_to_be_retrieved,
			paper_ids=final_paper_ids,
		)
		return retrieved_nodes

	async def aretrieve(
		self,
		item_to_be_retrieved: str,
		target_user_id: str = None,
	) -> List[NodeWithScore]:
		r"""
		This tool is used to retrieve academic information in the Laboratory's shared paper database.
		It is useful to help answer the user's academic questions.

		Args:
			item_to_be_retrieved (str): The things that you want to retrieve in the shared paper database.
			target_user_id (str): If given, the retrieval range will be confined to the papers belonging to the given user.
				Defaults to None.
		"""
		# This docstring is used as the tool description.
		# Retrieve in chunk nodes
		self._reset_retriever(target_user_id=target_user_id)
		chunk_nodes = await self.shared_paper_retriever.aretrieve(item_to_be_retrieved)
		paper_summaries = self.get_parent_summaries(chunk_nodes=chunk_nodes)
		if paper_summaries is None:
			return []

		final_paper_ids = await self.paper_summary_post_selector.aselect(
			item_to_be_retrieved=item_to_be_retrieved,
			paper_summaries=paper_summaries,
		)
		retrieved_nodes = await self.asecondary_retrieve(
			item_to_be_retrieved=item_to_be_retrieved,
			paper_ids=final_paper_ids,
		)
		return retrieved_nodes


if __name__ == "__main__":
	import asyncio
	from labridge.models.utils import get_models

	llm, embed_model = get_models()
	ss = SharedPaperRetriever.from_storage(
		llm=llm,
		embed_model=embed_model,
	)
	# retrieved_nodes = ss.retrieve(item_to_be_retrieved="Deep learning compiler", target_user_id="杨再正")

	# async def main():
	# 	retrieved_nodes = await ss.aretrieve(item_to_be_retrieved="Neural network quantization", target_user_id="杨再正")
	#
	# 	for node_score in retrieved_nodes:
	# 		rel_path = node_score.node.metadata.get(PAPER_REL_FILE_PATH, None)
	# 		print(rel_path)
	# 		if rel_path is None:
	# 			print(node_score.node.get_content())
	# 			print(node_score.node.node_id)
	# 			print(node_score.node.metadata)
	#
	# asyncio.run(main())

