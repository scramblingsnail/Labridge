import datetime
import llama_index.core.instrumentation as instrument

from llama_index.core.indices.vector_store.retrievers.retriever import VectorIndexRetriever
from llama_index.core.indices.vector_store.retrievers.retriever import BaseRetriever
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.vector_stores.types import FilterOperator
from llama_index.core import Settings
from llama_index.core.schema import (
    NodeWithScore,
    QueryBundle,
    QueryType,
)
from llama_index.core.vector_stores.types import (
	MetadataFilters,
	MetadataFilter,
)

from typing import List
from labridge.llm.models import get_models
from labridge.memory.chat.chat_memory import (
	ChatVectorMemory,
	CHAT_DATE_NAME,
	CHAT_TIME_NAME,
)
from labridge.common.chat.utils import (
	CHAT_DATE_FORMAT,
	str_to_datetime,
	str_to_date,
)


dispatcher = instrument.get_dispatcher(__name__)

# TODO: MetaData filter: date filter: use the operator `any`, generate the candidate date as the filter value. The date in metadata is a list

# TODO: retriever tool or query tool? 先用 retrieve tool 试一试。



CHAT_MEMORY_RELEVANT_TOP_K = 3


class ChatMemoryRetriever(BaseRetriever):
	r"""
	Note:
		The docstring of the Method `retrieve_with_date` will be used as the tool description of the corresponding
		retriever tool.
	"""
	def __init__(
		self,
		memory_index: ChatVectorMemory = None,
		memory_vector_retriever: VectorIndexRetriever = None,
		embed_model: BaseEmbedding = None,
		final_use_context: bool = True,
		relevant_top_k: int = CHAT_MEMORY_RELEVANT_TOP_K
	):
		super().__init__()
		self.memory_index = memory_index
		self.memory_vector_retriever = memory_vector_retriever
		self.embed_model = embed_model or Settings.embed_model
		self.final_use_context = final_use_context
		self.relevant_top_k = relevant_top_k

	@dispatcher.span
	def retrieve(self, str_or_query_bundle: QueryType) -> List[NodeWithScore]:
		raise Warning("In ChatMemoryRetriever, the `retrieve` method is not used, use the `retrieve_with_date` instead.")

	def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
		r""" Do not use this method. """
		return []

	def _parse_date(self, start_date_str: str, end_date_str: str):
		start_date = str_to_date(start_date_str)
		end_date = str_to_date(end_date_str)
		if end_date < start_date:
			raise ValueError("The end_date can not be earlier than the start_date!")

		date_list = []
		current_date = start_date
		while current_date <= end_date:
			date_list.append(current_date.strftime(CHAT_DATE_FORMAT))
			current_date = current_date + datetime.timedelta(days=1)
		return date_list

	def get_memory_vector_retriever(self) -> VectorIndexRetriever:
		memory_retriever = self.memory_index.vector_index.as_retriever(
			similarity_top_k=self.relevant_top_k,
			filters=None,
		)
		return memory_retriever

	def get_date_filters(self, date_list: List[str]) -> MetadataFilters:
		date_filter = MetadataFilter(
			key=CHAT_DATE_NAME,
			value=date_list,
			operator=FilterOperator.ANY,
		)
		return MetadataFilters(filters=[date_filter])

	def sort_retrieved_nodes(self, memory_nodes: List[NodeWithScore], descending: bool = False):
		if len(memory_nodes) < 1:
			return []
		nodes_datetime = []
		for node in memory_nodes:
			node_date_str = node.node.metadata[CHAT_DATE_NAME][0]
			node_time_str = node.node.metadata[CHAT_TIME_NAME][0]
			nodes_datetime.append(str_to_datetime(date_str=node_date_str, time_str=node_time_str))

		sorted_items = sorted(zip(memory_nodes, nodes_datetime), key=lambda x: x[1], reverse=descending)
		sorted_nodes, sorted_datetime = zip(*sorted_items)
		return sorted_nodes


	def _add_context(self, content_nodes: List[NodeWithScore]) -> List[NodeWithScore]:
		r"""
		Add the 1-hop context nodes of each content node and keep the QA time order.

		Only the context nodes whose date is the same as the retrieved node will be added.
		"""
		content_ids = [node.node.node_id for node in content_nodes]
		final_nodes = []
		for node in content_nodes:
			node_date = node.node.metadata[CHAT_DATE_NAME]
			prev_node_info = node.node.prev_node
			next_node_info = node.node.next_node
			if prev_node_info is not None:
				prev_id = prev_node_info.node_id
				prev_node = self.memory_index.vector_index._docstore.get_node(prev_id)
				if prev_id not in content_ids and prev_node.metadata[CHAT_DATE_NAME] == node_date:
					final_nodes.append(NodeWithScore(node=prev_node))

			final_nodes.append(node)

			if next_node_info is not None:
				next_id = next_node_info.node_id
				next_node = self.memory_index.vector_index._docstore.get_node(next_id)
				if next_id not in content_ids and next_node.metadata[CHAT_DATE_NAME] == node_date:
					final_nodes.append(NodeWithScore(node=next_node))
		final_nodes = self.sort_retrieved_nodes(memory_nodes=final_nodes)
		return final_nodes

	@dispatcher.span
	def retrieve_with_date(
		self,
		item_to_be_retrieved: str,
		memory_id: str,
		start_date: str,
		end_date: str,
	) -> List[NodeWithScore]:
		r"""
		This tool is used to retrieve relevant chat history in a certain chat history memory.
		The memory_id of a chat history memory is the `user_id` of a specific user or the `chat_group_id` of a specific
		chat group.

		Additionally, you can provide the `start_date` and `end_state` to limit the retrieving range of date,
		The end date can be the same as the start date, but should not be earlier than the start date.

		Args:
			item_to_be_retrieved (str): Things that you want to retrieve in the chat history memory.
			memory_id (str): The memory_id of a chat history memory. It is either a `user_id` or a `chat_group_id`.
			start_date (str): The START date of the retrieving date limit.
				It should be given in the following FORMAT: Year-Month-Day.
				For example, 2020-12-1 means the year 2020, the 12th month, the 1rst day.
			end_date (str): The END date of the retrieving date limit.
				It should be given in the following FORMAT: Year-Month-Day.
				For example, 2024-6-2 means the year 2024, the 6th month, the 2nd day.

		Returns:
			Retrieved chat history.
		"""

		# set self.memory_index according to the user_id.
		if self.memory_index is None or self.memory_index.memory_id != memory_id:
			self.memory_index = ChatVectorMemory.from_memory_id(
				memory_id=memory_id,
				embed_model=self.embed_model,
				retriever_kwargs={},
			)
			self.memory_vector_retriever = self.get_memory_vector_retriever()

		# get the candidate date list.
		date_list = self._parse_date(start_date_str=start_date, end_date_str=end_date)
		metadata_filters = self.get_date_filters(date_list=date_list)
		self.memory_vector_retriever._filters = metadata_filters
		chat_nodes = self.memory_vector_retriever.retrieve(item_to_be_retrieved)
		# get the results, add prev node and next node to it (if in a same date.).
		if self.final_use_context:
			chat_nodes = self._add_context(content_nodes=chat_nodes)
		return chat_nodes

	async def aretrieve_with_date(
		self,
		item_to_be_retrieved: str,
		memory_id: str,
		start_date: str,
		end_date: str,
	) -> List[NodeWithScore]:
		r"""
		This method is used to asynchronously retrieve relevant chat history in a certain chat history memory.
		The memory_id of a chat history memory is the `user_id` of a specific user or the `chat_group_id` of a specific
		chat group.

		Additionally, you can provide the `start_date` and `end_state` to limit the retrieving range of date,
		The end date should not be earlier than the start date.

		Args:
			item_to_be_retrieved (str): Things that you want to retrieve in the chat history memory.
			memory_id (str): The memory_id of a chat history memory. It is either a `user_id` or a `chat_group_id`.
			start_date (str): The START date of the retrieving date limit.
				It should be given in the following FORMAT: Year-Month-Day.
				For example, 2020-12-1 means the year 2020, the 12th month, the 1rst day.
			end_date (str): The END date of the retrieving date limit.
				It should be given in the following FORMAT: Year-Month-Day.
				For example, 2024-6-2 means the year 2024, the 6th month, the 2nd day.

		Returns:
			Retrieved chat history.
		"""
		# set self.memory_index according to the user_id.
		if self.memory_index is None or self.memory_index.memory_id != memory_id:
			self.memory_index = ChatVectorMemory.from_memory_id(
				memory_id=memory_id,
				embed_model=self.embed_model,
				retriever_kwargs={},
			)
			self.memory_vector_retriever = self.get_memory_vector_retriever()

		# get the candidate date list.
		date_list = self._parse_date(start_date_str=start_date, end_date_str=end_date)
		metadata_filters = self.get_date_filters(date_list=date_list)
		self.memory_vector_retriever._filters = metadata_filters
		chat_nodes = await self.memory_vector_retriever.aretrieve(item_to_be_retrieved)
		# get the results, add prev node and next node to it (if in a same date.).
		if self.final_use_context:
			chat_nodes = self._add_context(content_nodes=chat_nodes)
		return chat_nodes


if __name__ == "__main__":
	llm, embed_model = get_models()
	Settings.embed_model = embed_model
	rr = ChatMemoryRetriever()
	rr_nodes = rr.retrieve_with_date(
		memory_id="杨再正",
		start_date="2024-08-01",
		end_date="2024-08-01",
		str_or_query_bundle="PPO",
	)
	print(rr_nodes)

	# now = datetime.datetime(
	# 	year=2024,
	# 	month=8,
	# 	day=1,
	# 	hour=12,
	# 	minute=20,
	# 	second=2,
	# )
	# nn = datetime.datetime(
	# 	year=2024,
	# 	month=8,
	# 	day=1,
	# 	hour=12,
	# 	minute=20,
	# 	second=24,
	# )
	# print(nn > now)
