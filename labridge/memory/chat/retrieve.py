import llama_index.core.instrumentation as instrument

from llama_index.core.indices.vector_store.retrievers.retriever import VectorIndexRetriever
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core import Settings
from llama_index.core.schema import NodeWithScore
from llama_index.core.vector_stores.types import MetadataFilters

from typing import List, Any
from labridge.llm.models import get_models
from labridge.memory.chat.chat_memory import ChatVectorMemory

from labridge.memory.base import LogBaseRetriever


dispatcher = instrument.get_dispatcher(__name__)


CHAT_MEMORY_RELEVANT_TOP_K = 3


class ChatMemoryRetriever(LogBaseRetriever):
	r"""
	This is a retriever that retrieve in the permanent chat history of a user or a chat group.

	Args:
		embed_model (BaseEmbedding): The used embedding model, if not specified, will use the `Settings.embed_model`
		final_use_context (bool): Whether to add the context nodes of the retrieved log nodes to the final results.
			Defaults to True.
		relevant_top_k (int): The top-k relevant nodes in retrieving will be used as the retrieved results.
			Defaults to `CHAT_MEMORY_RELEVANT_TOP_K`.
	"""
	def __init__(
		self,
		embed_model: BaseEmbedding = None,
		final_use_context: bool = True,
		relevant_top_k: int = CHAT_MEMORY_RELEVANT_TOP_K
	):
		super().__init__(
			embed_model=embed_model,
			final_use_context=final_use_context,
			relevant_top_k=relevant_top_k,
		)

	def get_memory_vector_retriever(self) -> VectorIndexRetriever:
		memory_retriever = self.memory.vector_index.as_retriever(
			similarity_top_k=self.relevant_top_k,
			filters=None,
		)
		return memory_retriever

	def reset_vector_retriever(self):
		self.memory_vector_retriever._filters = None
		self.memory_vector_retriever._node_ids = None

	def get_memory_vector_index(self) -> VectorStoreIndex:
		return self.memory.vector_index

	@dispatcher.span
	def retrieve(
		self,
		item_to_be_retrieved: str,
		memory_id: str,
		start_date: str = None,
		end_date: str = None,
		**kwargs: Any,
	) -> List[NodeWithScore]:
		r"""
		This tool is used to retrieve relevant chat history in a certain chat history memory.
		The memory_id of a chat history memory is the `user_id` of a specific user or the `chat_group_id` of a specific
		chat group.

		Additionally, you can provide the `start_date` and `end_state` to limit the retrieving range of date,
		The end date can be the same as the start date, but should not be earlier than the start date.
		If the start date or end_date is not provided, retrieving will be performed among the whole memory.

		Args:
			item_to_be_retrieved (str): Things that you want to retrieve in the chat history memory.
			memory_id (str): The memory_id of a chat history memory. It is either a `user_id` or a `chat_group_id`.
			start_date (str): The START date of the retrieving date limit. Defaults to None.
				If given, it should be given in the following FORMAT: Year-Month-Day.
				For example, 2020-12-1 means the year 2020, the 12th month, the 1rst day.
			end_date (str): The END date of the retrieving date limit. Defaults to None.
				If given, It should be given in the following FORMAT: Year-Month-Day.
				For example, 2024-6-2 means the year 2024, the 6th month, the 2nd day.

		Returns:
			Retrieved chat history.
		"""

		# set self.memory_index according to the user_id.
		if self.memory is None or self.memory.memory_id != memory_id:
			self.memory = ChatVectorMemory.from_memory_id(memory_id=memory_id, embed_model=self.embed_model,
				retriever_kwargs={}, )
			self.memory_vector_retriever = self.get_memory_vector_retriever()

		# get the candidate date list.
		date_list = self._parse_date(start_date_str=start_date, end_date_str=end_date)
		metadata_filters =  MetadataFilters(
			filters=[
				self.get_date_filter(date_list=date_list),
			]
		)
		self.memory_vector_retriever._filters = metadata_filters
		chat_nodes = self.memory_vector_retriever.retrieve(item_to_be_retrieved)
		self.reset_vector_retriever()
		# get the results, add prev node and next node to it (if in a same date.).
		if self.final_use_context:
			chat_nodes = self._add_context(content_nodes=chat_nodes)
		return chat_nodes

	@dispatcher.span
	async def aretrieve(
		self,
		item_to_be_retrieved: str,
		memory_id: str,
		start_date: str = None,
		end_date: str = None,
		**kwargs: Any,
	) -> List[NodeWithScore]:
		r"""
		This method is used to asynchronously retrieve relevant chat history in a certain chat history memory.
		The memory_id of a chat history memory is the `user_id` of a specific user or the `chat_group_id` of a specific
		chat group.

		Additionally, you can provide the `start_date` and `end_state` to limit the retrieving range of date,
		The end date should not be earlier than the start date.
		If the start date or end_date is not provided, retrieving will be performed among the whole memory.

		Args:
			item_to_be_retrieved (str): Things that you want to retrieve in the chat history memory.
			memory_id (str): The memory_id of a chat history memory. It is either a `user_id` or a `chat_group_id`.
			start_date (str): The START date of the retrieving date limit. Defaults to None.
				If given, it should be given in the following FORMAT: Year-Month-Day.
				For example, 2020-12-1 means the year 2020, the 12th month, the 1rst day.
			end_date (str): The END date of the retrieving date limit. Defaults to None.
				If given, it should be given in the following FORMAT: Year-Month-Day.
				For example, 2024-6-2 means the year 2024, the 6th month, the 2nd day.

		Returns:
			Retrieved chat history.
		"""
		# set self.memory_index according to the user_id.
		if self.memory is None or self.memory.memory_id != memory_id:
			self.memory = ChatVectorMemory.from_memory_id(
				memory_id=memory_id,
				embed_model=self.embed_model,
				retriever_kwargs={},
			)
			self.memory_vector_retriever = self.get_memory_vector_retriever()

		# get the candidate date list.
		date_list = self._parse_date(start_date_str=start_date, end_date_str=end_date)
		metadata_filters = MetadataFilters(
			filters=[
				self.get_date_filter(date_list=date_list),
			]
		)
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
	rr_nodes = rr.retrieve(
		memory_id="杨再正",
		start_date="2024-08-01",
		end_date="2024-08-09",
		item_to_be_retrieved="PPO",
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
