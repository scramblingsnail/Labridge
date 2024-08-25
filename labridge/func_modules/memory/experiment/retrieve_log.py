import datetime
import llama_index.core.instrumentation as instrument

from llama_index.core.indices.vector_store.retrievers.retriever import VectorIndexRetriever
from llama_index.core.indices.vector_store.retrievers.retriever import BaseRetriever
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.vector_stores.types import FilterOperator
from llama_index.core import Settings
from llama_index.core.schema import (
    NodeWithScore,
    QueryBundle,
    QueryType,
	MetadataMode
)
from llama_index.core.vector_stores.types import (
	MetadataFilters,
	MetadataFilter,
)

from typing import List, Any
from labridge.models.utils import get_models
from labridge.func_modules.memory.experiment.experiment_log import ExperimentLog

from labridge.func_modules.memory.base import LogBaseRetriever


dispatcher = instrument.get_dispatcher(__name__)


EXPERIMENT_LOG_RELEVANT_TOP_K = 3


class ExperimentLogRetriever(LogBaseRetriever):
	r"""
	This class retrieve in a specific user's experiment logs.

	The docstring of the method `retrieve` or `aretrieve` are used as tool description of the
	corresponding retriever tool.

	Args:
		embed_model (BaseEmbedding): The embed model. Defaults to None.
			If set to None, the Settings.embed_model will be used.
		final_use_context (bool): Whether to add the context nodes of the retrieved nodes to the final results.
			Defaults to True.
		relevant_top_k (int): The `relevant_top_k` log nodes will be selected as the retrieved nodes.
			Defaults to `EXPERIMENT_LOG_RELEVANT_TOP_K`.
	"""
	def __init__(
		self,
		embed_model: BaseEmbedding = None,
		final_use_context: bool = True,
		relevant_top_k: int = None,
	):
		relevant_top_k = relevant_top_k or EXPERIMENT_LOG_RELEVANT_TOP_K
		super().__init__(
			embed_model=embed_model,
			final_use_context=final_use_context,
			relevant_top_k=relevant_top_k,
		)

	def get_memory_vector_index(self) -> VectorStoreIndex:
		r""" Get the vector index. """
		return self.memory.vector_index

	def get_memory_vector_retriever(self) -> VectorIndexRetriever:
		r""" Get the default vector index retriever, with default similarity_top_k and no date filters. """
		memory_retriever = self.memory.vector_index.as_retriever(
			similarity_top_k=self.relevant_top_k,
			filters=None,
		)
		return memory_retriever

	def reset_vector_retriever(self):
		r"""
		Reset the vector index retriever to defaults.
		Specifically, with no date filters and confined node ids.
		"""
		self.memory_vector_retriever._filters = [self._log_node_filter(),]
		self.memory_vector_retriever._node_ids = None

	@dispatcher.span
	def retrieve(
		self,
		item_to_be_retrieved: str,
		memory_id: str,
		start_date: str = None,
		end_date: str = None,
		experiment_name: str = None,
		**kwargs: Any,
	) -> List[NodeWithScore]:
		r"""
		This tool is used to retrieve experiment logs of a user.
		Use this tool to help you to answer questions about experimental records.

		Args:
			item_to_be_retrieved (str): This argument is necessary.
				It denotes things that you want to retrieve in the chat history memory.
			memory_id (str): This argument is necessary.
				It is the user_id of a lab member.
			start_date (str): This argument is optional.
				It denotes the start date in the format 'Year-Month-Day'.
				If both start_date and end_date are specified, only logs which are recorded between the
				start_date and end_date will be retrieved.
			end_date (str): This argument is optional.
				It denotes the end date in the format 'Year-Month-Day'.
			experiment_name (str): This argument is optional.
				It is the name of a specific experiment.
				If it is specified and is valid, only logs of this experiment will be retrieved.
			kwargs: Other arguments will be ignored.

		Returns:
			Retrieved experiment logs.
		"""
		if self.memory is None or self.memory.memory_id != memory_id:
			self.memory = ExperimentLog.from_user_id(
				user_id=memory_id,
				embed_model=self.embed_model,
			)
			self.memory_vector_retriever = self.get_memory_vector_retriever()

		self.reset_vector_retriever()

		if experiment_name is None or not self.memory.is_expr_exist(experiment_name):
			retrieve_node_ids = None
		else:
			retrieve_node_ids = self.memory.get_expr_log_node_ids(experiment_name)

		filters = [self._log_node_filter(),]
		if None not in [start_date, end_date]:
			# get the candidate date list.
			date_list = self._parse_date(start_date_str=start_date, end_date_str=end_date)
			filters.append(
				self.get_date_filter(date_list=date_list),
			)

		metadata_filters = MetadataFilters(filters=filters)

		self.memory_vector_retriever._filters = metadata_filters
		self.memory_vector_retriever._node_ids = retrieve_node_ids

		# TODO: hybrid retrieve: add retrieve experiment.
		log_nodes = self.memory_vector_retriever.retrieve(item_to_be_retrieved)

		if self.final_use_context:
			log_nodes = self._add_context(content_nodes=log_nodes)
		return log_nodes

	@dispatcher.span
	async def aretrieve(
		self,
		item_to_be_retrieved: str,
		memory_id: str,
		start_date: str = None,
		end_date: str = None,
		experiment_name: str = None,
		**kwargs: Any,
	) -> List[NodeWithScore]:
		r"""
		This tool is used to retrieve relevant experiment logs in a certain experiment log memory.

		Args:
			item_to_be_retrieved (str): This argument is necessary.
				It denotes things that you want to retrieve in the chat history memory.
			memory_id (str): This argument is necessary.
				It is the user_id of a lab member.
			start_date (str): This argument is optional.
				It denotes the start date in the format 'Year-Month-Day'.
				If both start_date and end_date are specified, only logs which are recorded between the
				start_date and end_date will be retrieved.
			end_date (str): This argument is optional.
				It denotes the end date in the format 'Year-Month-Day'.
			experiment_name (str): This argument is optional.
				It is the name of a specific experiment.
				If it is specified and is valid, only logs of this experiment will be retrieved.
			kwargs: Other arguments will be ignored.

		Returns:
			Retrieved experiment logs.
		"""
		if self.memory is None or self.memory.memory_id.user_id != memory_id:
			self.memory = ExperimentLog.from_user_id(
				user_id=memory_id,
				embed_model=self.embed_model,
			)
			self.memory_vector_retriever = self.get_memory_vector_retriever()

		self.reset_vector_retriever()

		if experiment_name is None or not self.memory.is_expr_exist(experiment_name):
			retrieve_node_ids = None
		else:
			retrieve_node_ids = self.memory.get_expr_log_node_ids(experiment_name)

		filters = [self._log_node_filter(), ]
		if None not in [start_date, end_date]:
			# get the candidate date list.
			date_list = self._parse_date(start_date_str=start_date, end_date_str=end_date)
			filters.append(
				self.get_date_filter(date_list=date_list)
			)

		metadata_filters = MetadataFilters(filters=filters)

		self.memory_vector_retriever._filters = metadata_filters
		self.memory_vector_retriever._node_ids = retrieve_node_ids
		log_nodes = await self.memory_vector_retriever.aretrieve(item_to_be_retrieved)

		for log_node in log_nodes:
			print(log_node.get_content(metadata_mode=MetadataMode.LLM), log_node.node.metadata)

		if self.final_use_context:
			log_nodes = self._add_context(content_nodes=log_nodes)
		return log_nodes


if __name__ == "__main__":
	# TODO: to be validated.
	import time
	from labridge.func_modules.memory.experiment.experiment_log import ExperimentLog
	from labridge.models.utils import get_models
	from llama_index.core.schema import MetadataMode

	llm, embed_model = get_models()

	logger = ExperimentLog.from_user_id(
		user_id="杨再正",
		embed_model=embed_model,
	)

	new_expr_id = "高均一性忆阻器阵列制备"
	expr_1_id = "强化学习优化忆阻器写入策略"

	# logger.create_experiment(
	# 	experiment_name=new_expr_id,
	# 	description="通过光刻、真空镀膜、刻蚀、原子层沉积系统制备高均一性的忆阻器交叉阵列"
	# )
	# time.sleep(1)
	# logger.create_experiment(
	# 	experiment_name=expr_1_id,
	# 	description="利用强化学习优化忆阻器写入策略"
	# )
	# time.sleep(1)
	# logger.put(
	# 	experiment_name=expr_1_id,
	# 	log_str="开始写TD3代码"
	# )
	# time.sleep(1)
	# logger.put(
	# 	experiment_name=expr_1_id,
	# 	log_str="开始写SAC代码"
	# )
	# time.sleep(1)
	# logger.put(
	# 	experiment_name=expr_1_id,
	# 	log_str="开始写PPO代码"
	# )
	# time.sleep(1)
	# logger.put(
	# 	experiment_name=new_expr_id,
	# 	log_str="今天的原子层沉积温度是 85摄氏度."
	# )
	# time.sleep(1)
	# logger.put(
	# 	experiment_name=new_expr_id,
	# 	log_str="今天的光刻曝光时间是0.8s, 显影时间是20s."
	# )
	# time.sleep(1)
	# logger.put(
	# 	experiment_name=new_expr_id,
	# 	log_str="今天的蒸镀电子束电流是 0.2A."
	# )
	#
	# logger.persist()

	log_retriever = ExperimentLogRetriever(
		embed_model=embed_model
	)

	nodes = log_retriever.retrieve(
		item_to_be_retrieved="曝光时间",
		memory_id="杨再正",
		start_date="2024-08-19",
		end_date="2024-08-19",
	)
	for node in nodes:
		print("Final: ", node.get_content(metadata_mode=MetadataMode.LLM))

	# from inspect import signature
	# from llama_index.core.tools.retriever_tool import RetrieverTool
	# print(f"{signature(ExperimentLogRetriever.retrieve)}")
