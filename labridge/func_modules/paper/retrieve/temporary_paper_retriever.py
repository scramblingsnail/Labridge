from llama_index.core.embeddings import BaseEmbedding
from llama_index.core import Settings
import llama_index.core.instrumentation as instrument
import fsspec
from llama_index.core.schema import NodeWithScore
from llama_index.core.indices.vector_store.retrievers.retriever import VectorIndexRetriever
from llama_index.core.vector_stores.types import FilterOperator
from llama_index.core.vector_stores.types import (
	MetadataFilters,
	MetadataFilter,
)

from labridge.common.utils.time import parse_date_list
from labridge.func_modules.paper.store.temorary_store import (
	RecentPaperStore,
	TMP_PAPER_DATE,
	TMP_PAPER_NODE_TYPE_KEY,
	TMP_PAPER_DOC_NODE_TYPE,
)

from typing import Any, List


dispatcher = instrument.get_dispatcher(__name__)

RECENT_PAPER_INFO_SIMILARITY_TOP_K = 5
RECENT_PAPER_SIMILARITY_TOP_K = 3


class RecentPaperRetriever:
	r"""
	This class is the retriever that retrieving in the recent papers store of a specific user.

	Args:
		embed_model (BaseEmbedding): The used embedding model. If not specified, the `Settings.embed_model` will be used.
		final_use_context (bool): Whether to use the context nodes as parts of the retrieved results.
		first_top_k (int): The `similarity_top_k` in the first retrieving.
			Refer to the method `retrieve` for details.
		secondary_top_k (int): The `similarity_top_k` in the secondary retrieving.
			Refer to the method `retrieve` for details.
	"""
	def __init__(
		self,
		embed_model: BaseEmbedding,
		final_use_context: bool = True,
		first_top_k: int = None,
		secondary_top_k: int = None,
	):
		self.paper_store = None
		self.paper_retriever = None
		self._embed_model = embed_model or Settings.embed_model
		self._final_use_context = final_use_context
		self._first_top_k = first_top_k or RECENT_PAPER_INFO_SIMILARITY_TOP_K
		self._relevant_top_k = secondary_top_k or RECENT_PAPER_SIMILARITY_TOP_K
		self.fs = fsspec.filesystem("file")

	def _add_context(
		self,
		content_nodes: List[NodeWithScore]
	) -> List[NodeWithScore]:
		r"""
		Add context nodes for the retrieved nodes.

		Args:
			content_nodes (List[NodeWithScore]): The retrieved nodes.

		Returns:
			List[NodeWithScore]: Concatenated nodes including context nodes.
		"""
		vector_index = self.paper_store.vector_index
		existing_ids = [node.node_id for node in content_nodes]
		final_nodes = []

		for node in content_nodes:
			prev_node_info = node.node.prev_node
			next_node_info = node.node.next_node
			if prev_node_info is not None:
				prev_id = prev_node_info.node_id
				if prev_id not in existing_ids:
					existing_ids.append(prev_id)
					prev_node = vector_index.docstore.get_node(node_id=prev_id)
					final_nodes.append(NodeWithScore(node=prev_node))
			final_nodes.append(node)
			if next_node_info is not None:
				next_id = next_node_info.node_id
				if next_id not in existing_ids:
					existing_ids.append(next_id)
					next_node = vector_index.docstore.get_node(node_id=next_id)
					final_nodes.append(NodeWithScore(node=next_node))
		return final_nodes

	def get_paper_retriever(self) -> VectorIndexRetriever:
		r"""
		Get the default paper retriever, with a node_type_filter.

		Returns:
			VectorIndexRetriever: The paper retriever.
		"""
		paper_retriever = self.paper_store.vector_index.as_retriever(
			similarity_top_k=self._relevant_top_k,
			filters=MetadataFilters(
				filters=[self.node_type_filter]
			),
		)
		return paper_retriever

	@property
	def node_type_filter(self) -> MetadataFilter:
		r"""
		The node type filter that filters nodes with type `TMP_PAPER_DOC_NODE_TYPE`.

		Returns:
			MetadataFilter: The node type metadata filter.
		"""
		doc_node_filter = MetadataFilter(
			key=TMP_PAPER_NODE_TYPE_KEY,
			value=TMP_PAPER_DOC_NODE_TYPE,
			operator=FilterOperator.EQ,
		)
		return doc_node_filter

	def get_date_filter(self, date_list: List[str]) -> MetadataFilter:
		r"""
		Get the date filter that filters according to the creation date of nodes.

		Args:
			date_list (List[str]): The date candidates. Only nodes created in one of these dates will be retrieved.

		Returns:
			MetadataFilter: The date filter.
		"""
		date_filter = MetadataFilter(
			key=TMP_PAPER_DATE,
			value=date_list,
			operator=FilterOperator.ANY,
		)
		return date_filter

	def reset_retriever(self):
		r"""
		Reset the paper retriever:

		- reset the node_ids that confine the retrieving range.
		- reset the similarity_top_k.
		- reset the MetadataFilters.

		Returns:
			None.
		"""
		if self.paper_retriever:
			self.paper_retriever._node_ids = None
			self.paper_retriever._similarity_top_k = self._first_top_k
			self.paper_retriever._filters = MetadataFilters(
				filters=[self.node_type_filter,]
			)

	def first_retrieve(self, paper_info: str) -> List[str]:
		r"""
		First retrieve: retrieve according to the paper_info.

		Args:
			paper_info (str): The information about the paper.

		Returns:
			List[str]: all the node ids of relevant papers.
		"""
		self.paper_retriever._similarity_top_k = self._first_top_k
		info_relevant_nodes = self.paper_retriever.retrieve(paper_info)
		confine_node_ids = self.paper_store.get_all_relevant_node_ids(
			node_ids=[node.node_id for node in info_relevant_nodes]
		)
		return confine_node_ids

	async def afirst_retrieve(self, paper_info: str) -> List[str]:
		r"""
		First retrieve: retrieve according to the paper_info.

		Args:
			paper_info (str): The information about the paper.

		Returns:
			List[str]: all the node ids of relevant papers.
		"""
		self.paper_retriever._similarity_top_k = self._first_top_k
		info_relevant_nodes = await self.paper_retriever.aretrieve(paper_info)
		confine_node_ids = self.paper_store.get_all_relevant_node_ids(
			node_ids=[node.node_id for node in info_relevant_nodes]
		)
		return confine_node_ids

	def secondary_retrieve(
		self,
		item_to_be_retrieved: str,
		confine_node_ids: List[str],
	) -> List[NodeWithScore]:
		r"""
		Secondary retrieve in the confined nodes range.

		Args:
			item_to_be_retrieved (str): The aspects to be retrieved in a paper.
			confine_node_ids (List[str]): The confined node ids.

		Returns:
			List[NodeWithScore]: The retrieved relevant nodes.
		"""
		self.paper_retriever._node_ids = confine_node_ids
		nodes = self.paper_retriever.retrieve(item_to_be_retrieved)
		return nodes

	async def asecondary_retrieve(
		self,
		item_to_be_retrieved: str,
		confine_node_ids: List[str],
	) -> List[NodeWithScore]:
		r"""
		Asynchronous secondary retrieve in the confined nodes range.

		Args:
			item_to_be_retrieved (str): The aspects to be retrieved in a paper.
			confine_node_ids (List[str]): The confined node ids.

		Returns:
			List[NodeWithScore]: The retrieved relevant nodes.
		"""
		self.paper_retriever._node_ids = confine_node_ids
		nodes = await self.paper_retriever.aretrieve(item_to_be_retrieved)
		return nodes

	@dispatcher.span
	def retrieve(
		self,
		paper_info: str,
		item_to_be_retrieved: str,
		user_id: str,
		start_date: str = None,
		end_date: str = None,
		**kwargs: Any,
	) -> List[NodeWithScore]:
		r"""
		This tool is used to retrieve in the recent papers storage of a specific user.
		These information should be provided:
		1. The paper information, such as title or save path.
		2. The specific question that you want to obtain answer from the paper.
		3. The user id.

		Args:
			paper_info (str): This argument is necessary.
				It is the relevant information of the paper.
				For example, it can be the paper title, or its save path.
			item_to_be_retrieved (str): This argument is necessary.
				It denotes the specific question that you want to retrieve in a specific paper.
			user_id (str): This argument is necessary.
				The user_id of a lab member.
			start_date (str): This argument is optional. It denotes the start date in the format 'Year-Month-Day'.
				If both start_date and end_date are specified, only papers which are added to storage between the
				start_date and end_date will be retrieved.
			end_date: This argument is optional. It denotes the end date in the format 'Year-Month-Day'.
			**kwargs: Other keyword arguments will be ignored.

		Returns:
			The retrieved results.
		"""
		# This docstring is used as the corresponding tool description.
		if self.paper_store is None or self.paper_store.user_id != user_id:
			self.paper_store = RecentPaperStore.from_user_id(
				user_id=user_id,
				embed_model=self._embed_model,
			)
			self.paper_retriever = self.get_paper_retriever()

		self.reset_retriever()

		# if new file
		if self.fs.exists(paper_info) and not self.paper_store.file_exists(file_path=paper_info):
			self.paper_store.put(paper_file_path=paper_info)

		if None not in [start_date, end_date]:
			# get the candidate date list.
			date_list = parse_date_list(start_date_str=start_date, end_date_str=end_date)
			metadata_filters = MetadataFilters(
				filters=[
					self.node_type_filter,
					self.get_date_filter(date_list=date_list),
				]
			)
			self.paper_retriever._filters = metadata_filters

		node_ids_range = self.first_retrieve(paper_info=paper_info)
		relevant_nodes = self.secondary_retrieve(
			item_to_be_retrieved=item_to_be_retrieved,
			confine_node_ids=node_ids_range,
		)
		if self._final_use_context:
			relevant_nodes = self._add_context(content_nodes=relevant_nodes)

		return relevant_nodes

	@dispatcher.span
	async def aretrieve(
		self,
		paper_info: str,
		item_to_be_retrieved: str,
		user_id: str,
		start_date: str = None,
		end_date: str = None,
		**kwargs: Any,
	) -> List[NodeWithScore]:
		r"""
		This tool is used to retrieve in the recent papers storage of a specific user.
		These information should be provided:
		1. The paper information, such as title or save path.
		2. The specific question that you want to obtain answer from the paper.
		3. The user id.

		Args:
			paper_info (str): This argument is necessary.
				It is the relevant information of the paper.
				For example, it can be the paper title, or its save path.
			item_to_be_retrieved (str): This argument is necessary.
				It denotes the specific question that you want to retrieve in a specific paper.
			user_id (str): This argument is necessary.
				The user_id of a lab member.
			start_date (str): This argument is optional. It denotes the start date in the format 'Year-Month-Day'.
				If both start_date and end_date are specified, only papers which are added to storage between the
				start_date and end_date will be retrieved.
			end_date: This argument is optional. It denotes the end date in the format 'Year-Month-Day'.
			**kwargs: Other keyword arguments will be ignored.

		Returns:
			The retrieved results.
		"""
		# This docstring is used as the corresponding tool description.
		if self.paper_store is None or self.paper_store.user_id != user_id:
			self.paper_store = RecentPaperStore.from_user_id(
				user_id=user_id,
				embed_model=self._embed_model,
			)
			self.paper_retriever = self.get_paper_retriever()

		self.reset_retriever()

		if self.fs.exists(paper_info) and not self.paper_store.file_exists(file_path=paper_info):
			self.paper_store.put(paper_file_path=paper_info)

		if None not in [start_date, end_date]:
			# get the candidate date list.
			date_list = parse_date_list(start_date_str=start_date, end_date_str=end_date)
			metadata_filters = MetadataFilters(
				filters=[
					self.node_type_filter,
					self.get_date_filter(date_list=date_list),
				]
			)
			self.paper_retriever._filters = metadata_filters

		node_ids_range = await self.afirst_retrieve(paper_info=paper_info)
		relevant_nodes = await self.asecondary_retrieve(
			item_to_be_retrieved=item_to_be_retrieved,
			confine_node_ids=node_ids_range,
		)
		if self._final_use_context:
			relevant_nodes = self._add_context(content_nodes=relevant_nodes)
		return relevant_nodes
