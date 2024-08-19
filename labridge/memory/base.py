import llama_index.core.instrumentation as instrument

from llama_index.core.indices.vector_store.retrievers.retriever import VectorIndexRetriever
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.vector_stores.types import FilterOperator
from llama_index.core import Settings
from llama_index.core.schema import NodeWithScore
from llama_index.core.vector_stores.types import MetadataFilter

from typing import List, Any
from abc import abstractmethod
from labridge.common.utils.time import (
	str_to_datetime,
	parse_date_list,
)


dispatcher = instrument.get_dispatcher(__name__)


CHAT_MEMORY_RELEVANT_TOP_K = 3


LOG_DATE_NAME = "date"
LOG_TIME_NAME = "time"

MEMORY_NODE_TYPE_NAME = "node_type"
LOG_NODE_TYPE = "log_node"
NOT_LOG_NODE_TYPE = "not_log_node"


class LogBaseRetriever(object):
	r"""
	This is the base class for log-type information retriever, such as chat history and experiment log.

	The attributes `memory` and `memory_vector_retriever` should be specified in the subclass,
	and they will be updated in the method `retrieve`.

	Args:
		embed_model (BaseEmbedding): The used embedding model.
		final_use_context (bool): Whether to use the context nodes of the retrieved nodes as the final results.
		relevant_top_k (int): The top-k relevant retrieved nodes will be used.

	Note:
		The docstring of the Method `retrieve` will be used as the tool description of the corresponding
		retriever tool.
	"""
	def __init__(
		self,
		embed_model: BaseEmbedding,
		final_use_context: bool,
		relevant_top_k: int,
	):
		self.memory = None
		self.memory_vector_retriever = None
		self.embed_model = embed_model or Settings.embed_model
		self.final_use_context = final_use_context
		self.relevant_top_k = relevant_top_k

	def _parse_date(self, start_date_str: str, end_date_str: str) -> List[str]:
		r"""
		Get the strings of dates that between the start date and the end date (including them).

		Args:
			start_date_str (str): The string of the start date in a specific format, specified in `common.utils.time`.
			end_date_str (str): The string of the end date.

		Returns:
		"""
		return parse_date_list(
			start_date_str=start_date_str,
			end_date_str=end_date_str,
		)

	@abstractmethod
	def get_memory_vector_retriever(self) -> VectorIndexRetriever:
		r""" Get the vector index retriever from the memory """

	@abstractmethod
	def get_memory_vector_index(self) -> VectorStoreIndex:
		r""" Get the vector index """

	def get_date_filter(self, date_list: List[str]) -> MetadataFilter:
		r"""
		Return the MetadataFilter that filters nodes with dates in the date_list.

		Args:
			date_list (List[str]): The candidate date strings.

		Returns:
			MetadataFilter: The date filter.
		"""
		date_filter = MetadataFilter(
			key=LOG_DATE_NAME,
			value=date_list,
			operator=FilterOperator.ANY,
		)
		return date_filter

	def _log_node_filter(self) -> MetadataFilter:
		r"""
		Return the filter that filters `LOG_NODE_TYPE` nodes.

		Returns:
			The node_type filter.
		"""
		log_type_filter = MetadataFilter(
			key=MEMORY_NODE_TYPE_NAME,
			value=LOG_NODE_TYPE,
			operator=FilterOperator.EQ,
		)
		return log_type_filter

	def sort_retrieved_nodes(
		self,
		memory_nodes: List[NodeWithScore],
		descending: bool = False,
	) -> List[NodeWithScore]:
		r"""
		Sort the retrieved nodes according datetime.

		Args:
			memory_nodes (List[NodeWithScore]): The retrieved nodes.
			descending (bool): Sort in descending order. Defaults to False.

		Returns:
			List[NodeWithScore]: The sorted nodes.
		"""
		if len(memory_nodes) < 1:
			return []
		nodes_datetime = []
		for node in memory_nodes:
			node_date_str = node.node.metadata[LOG_DATE_NAME][0]
			node_time_str = node.node.metadata[LOG_TIME_NAME][0]
			nodes_datetime.append(str_to_datetime(date_str=node_date_str, time_str=node_time_str))

		sorted_items = sorted(zip(memory_nodes, nodes_datetime), key=lambda x: x[1], reverse=descending)
		sorted_nodes, sorted_datetime = zip(*sorted_items)
		return sorted_nodes

	def _add_context(self, content_nodes: List[NodeWithScore]) -> List[NodeWithScore]:
		r"""
		Add the 1-hop context nodes of each content node and keep the QA time order.
		Only the context nodes whose date is the same as the retrieved node will be added.

		Args:
			content_nodes (List[NodeWithScore]): The retrieved nodes.

		Returns:
			List[NodeWithScore]: The final nodes including the context nodes.
		"""
		existing_ids = [node.node.node_id for node in content_nodes]
		final_nodes = []
		vector_index = self.get_memory_vector_index()
		for node in content_nodes:
			# print(node.get_content())
			node_date = node.node.metadata[LOG_DATE_NAME]
			prev_node_info = node.node.prev_node
			next_node_info = node.node.next_node
			if prev_node_info is not None:
				prev_id = prev_node_info.node_id
				prev_node = vector_index.docstore.get_node(prev_id)
				if prev_id not in existing_ids and prev_node.metadata[LOG_DATE_NAME] == node_date:
					existing_ids.append(prev_id)
					final_nodes.append(NodeWithScore(node=prev_node))

			final_nodes.append(node)

			if next_node_info is not None:
				next_id = next_node_info.node_id
				next_node = vector_index.docstore.get_node(next_id)
				if next_id not in existing_ids and next_node.metadata[LOG_DATE_NAME] == node_date:
					existing_ids.append(next_id)
					final_nodes.append(NodeWithScore(node=next_node))
		final_nodes = self.sort_retrieved_nodes(memory_nodes=final_nodes)
		return final_nodes

	@dispatcher.span
	@abstractmethod
	def retrieve(
		self,
		item_to_be_retrieved: str,
		memory_id: str,
		start_date: str = None,
		end_date: str = None,
		**kwargs: Any,
	) -> List[NodeWithScore]:
		r"""
		The docstring of this Method will be used as the tool description of the corresponding retriever tool.
		"""

	@dispatcher.span
	@abstractmethod
	async def aretrieve(
		self,
		item_to_be_retrieved: str,
		memory_id: str,
		start_date: str = None,
		end_date: str = None,
		**kwargs: Any,
	) -> List[NodeWithScore]:
		r"""
		The docstring of this Method will be used as the tool description of the corresponding retriever tool.
		"""
