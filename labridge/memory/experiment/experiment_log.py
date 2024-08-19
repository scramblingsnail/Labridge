import fsspec
import uuid

from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core import load_index_from_storage
from llama_index.core.storage import StorageContext
from llama_index.core.schema import (
	TextNode,
	NodeRelationship,
	RelatedNodeInfo,
	BaseNode,
)

from pathlib import Path
from typing import List, Optional, Dict

from labridge.accounts.users import AccountManager
from labridge.common.utils.time import get_time, str_to_datetime
from labridge.llm.models import get_models
from labridge.memory.base import LOG_DATE_NAME, LOG_TIME_NAME, MEMORY_NODE_TYPE_NAME, LOG_NODE_TYPE, NOT_LOG_NODE_TYPE


EXPERIMENT_LOG_PERSIST_DIR = "storage/experiment_log"
EXPERIMENT_LOG_VECTOR_INDEX_ID = "experiment_log"

EXPERIMENT_INSTRUMENT_NAME = "instruments"

INIT_NODE_NAME = "root_node"
RECENT_EXPERIMENT_NODE_NAME = "recent_experiment"
EXPERIMENT_LAST_NODE_ID_PREFIX = "last_log"

RECENT_EXPERIMENT_NAME_KEY = "experiment_name"
RECENT_EXPERIMENT_START_TIME_KEY = "start_time"
RECENT_EXPERIMENT_END_TIME_KEY = "end_time"



class ExperimentLog(object):
	r"""
	This class stores the experiment logs for a specific user.
	It is constructed as a tree, with a root node. Different experiments are inserted as child nodes of the tree node.
	For each experiment node, TextNodes recording experiment logs are stored as its child nodes in chronological order.
	Like:

	```
											root_node
										/				\
									   /				 \
								Experiment1			Experiment2
						/		...				\
					log1 --next-> ... --next-> log n
	```

	Additionally, a recent_experiment node records the most recent experiment of the user, with the start time and the
	end time of the experiment.

	Note:
		The metadata `date` and `time` is recorded in a list format for the convenience of metadata filtering.
		For example: ['2024-08-10'], ['09:05:03'].
	"""
	def __init__(self, vector_index: VectorStoreIndex, persist_dir: str):
		self.vector_index = vector_index
		self.vector_index.set_index_id(EXPERIMENT_LOG_VECTOR_INDEX_ID)
		self.persist_dir = persist_dir

	@classmethod
	def from_storage(
		cls,
		persist_dir: str,
		embed_model: BaseEmbedding,
	):
		vector_storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
		vector_index = load_index_from_storage(
			storage_context=vector_storage_context,
			index_id=EXPERIMENT_LOG_VECTOR_INDEX_ID,
			embed_model=embed_model,
		)
		return cls(
			vector_index=vector_index,
			persist_dir=persist_dir,
		)

	@property
	def user_id(self)->str:
		r""" Get the user_id """
		root = Path(__file__)
		for idx in range(4):
			root = root.parent

		user_id = Path(self.persist_dir).relative_to(root / EXPERIMENT_LOG_PERSIST_DIR)
		return str(user_id)

	def update(self):
		return self.from_user_id(
			user_id=self.user_id,
			embed_model=self.vector_index._embed_model,
		)

	@classmethod
	def from_user_id(
		cls,
		user_id: str,
		embed_model: BaseEmbedding,
	):
		account_manager = AccountManager()
		account_manager.check_valid_user(user_id=user_id)

		root = Path(__file__)
		for idx in range(4):
			root = root.parent

		persist_dir = str(root / f"{EXPERIMENT_LOG_PERSIST_DIR}/{user_id}")
		fs = fsspec.filesystem("file")
		if fs.exists(persist_dir):
			return cls.from_storage(
				persist_dir=persist_dir,
				embed_model=embed_model,
			)

		# root node.
		date, h_m_s = get_time()
		root_node = TextNode(
			text=f"Root node for the experiment logs of {user_id}",
			id_=INIT_NODE_NAME,
			metadata={
				LOG_DATE_NAME: [date,],
				LOG_TIME_NAME: [h_m_s,],
				MEMORY_NODE_TYPE_NAME: NOT_LOG_NODE_TYPE,
			}
		)
		# record the most recent experiment.
		recent_expr_node = TextNode(
			text=f"The most recent experiment of the user {user_id}",
			id_=RECENT_EXPERIMENT_NODE_NAME,
			metadata={
				RECENT_EXPERIMENT_NAME_KEY: None,
				RECENT_EXPERIMENT_START_TIME_KEY: None,
				RECENT_EXPERIMENT_END_TIME_KEY: None,
				LOG_DATE_NAME: [date,],
				LOG_TIME_NAME: [h_m_s,],
				MEMORY_NODE_TYPE_NAME: NOT_LOG_NODE_TYPE,
			}
		)
		nodes = [root_node, recent_expr_node]
		vector_index = VectorStoreIndex(
			nodes=nodes,
			embed_model=embed_model,
		)
		return cls(
			vector_index=vector_index,
			persist_dir=persist_dir,
		)

	def get_recent_experiment(self) -> Optional[str]:
		r""" Get the most recent experiment name. """
		recent_node = self._get_node(node_id=RECENT_EXPERIMENT_NODE_NAME)
		metadata = recent_node.metadata

		expr_name = metadata[RECENT_EXPERIMENT_NAME_KEY]
		if expr_name is None:
			return None

		start_date_str, start_time_str = metadata[RECENT_EXPERIMENT_START_TIME_KEY]
		end_date_str, end_time_str = metadata[RECENT_EXPERIMENT_END_TIME_KEY]

		try:
			start = str_to_datetime(date_str=start_date_str, time_str=start_time_str)
			end = str_to_datetime(date_str=end_date_str, time_str=end_time_str)
			date, h_m_s = get_time()
			current = str_to_datetime(date_str=date, time_str=h_m_s)
			if start <= current <= end:
				return expr_name
			return None
		except Exception as e:
			print(f"Error in get_recent_experiment: {e}")
			return None

	def get_all_experiments(self) -> Optional[List[str]]:
		r""" Get all experiment names. """
		root_node = self._get_node(node_id=INIT_NODE_NAME)
		expr_list = root_node.child_nodes
		if expr_list:
			return [expr.node_id for expr in expr_list]
		return None

	def get_all_experiments_with_description(self) -> Optional[Dict[str, str]]:
		root_node = self._get_node(node_id=INIT_NODE_NAME)
		expr_list = root_node.child_nodes

		experiments = {}
		if expr_list:
			for child in expr_list:
				expr_id = child.node_id
				expr_node = self._get_node(node_id=expr_id)
				experiments[expr_id] = expr_node.text
			return experiments
		return None

	def set_recent_experiment(
		self,
		experiment_name: str,
		start_date: str,
		start_time: str,
		end_date: str,
		end_time: str,
	):
		r""" Set the most recent (or actually, current) experiment and its duration. """
		expr_list = self.get_all_experiments()
		if experiment_name not in expr_list:
			raise ValueError(
				f"The experiment {experiment_name} " 
				f"does not exist in the experiment log memory of the user {self.user_id}"
			)

		recent_node = self._get_node(node_id=RECENT_EXPERIMENT_NODE_NAME)
		recent_node.metadata[RECENT_EXPERIMENT_START_TIME_KEY] = (
			start_date, start_time
		)
		recent_node.metadata[RECENT_EXPERIMENT_END_TIME_KEY] = (
			end_date, end_time
		)
		recent_node.metadata[RECENT_EXPERIMENT_NAME_KEY] = experiment_name
		self._update_node(
			node_id=RECENT_EXPERIMENT_NODE_NAME,
			node=recent_node,
		)

	def _get_node(self, node_id: str) -> BaseNode:
		return self.vector_index.docstore.get_node(node_id)

	def _update_node(
		self,
		node_id: str,
		node: BaseNode,
	):
		self.vector_index.delete_nodes([node_id])
		self.vector_index.insert_nodes([node])

	def is_expr_exist(self, experiment_name: str) -> bool:
		r""" Whether a experiment exists. """
		root_node = self._get_node(node_id=INIT_NODE_NAME)
		expr_list = root_node.relationships[NodeRelationship.CHILD]
		return experiment_name in [expr.node_id for expr in expr_list]

	def get_expr_log_node_ids(self, experiment_name: str) -> List[str]:
		r""" Get the log node ids of a specific experiment. """
		expr_node = self._get_node(node_id=experiment_name)
		return [log_node.node_id for log_node in expr_node.child_nodes]

	def create_experiment(self, experiment_name: str, description: str):
		r""" Add a new experiment. """
		root_node = self._get_node(node_id=INIT_NODE_NAME)
		expr_list = root_node.child_nodes or []
		if experiment_name in [expr.node_id for expr in expr_list]:
			raise ValueError(f"The experiment name {experiment_name} already exists.")

		new_expr_node = self._new_node(
			text=description,
			node_id=experiment_name,
			node_type=NOT_LOG_NODE_TYPE,
		)

		expr_header_node = self._new_node(
			text=f"The log beginning of the experiment {experiment_name}",
			node_id=f"{experiment_name}_header",
			node_type=LOG_NODE_TYPE
		)

		last_info_node = self._new_node(
			text=expr_header_node.node_id,
			node_id=f"{experiment_name}_{EXPERIMENT_LAST_NODE_ID_PREFIX}",
			node_type=NOT_LOG_NODE_TYPE,
		)

		expr_list.append(
			RelatedNodeInfo(node_id=new_expr_node.node_id)
		)
		root_node.relationships[NodeRelationship.CHILD] = expr_list
		self._update_node(node_id=INIT_NODE_NAME, node=root_node)

		self.vector_index.insert_nodes(
			[
				new_expr_node,
				expr_header_node,
				last_info_node,
			]
		)

	def _new_node(
		self,
		text: str,
		node_type: str,
		node_id: str = None,
	) -> TextNode:
		date, h_m_s = get_time()
		node = TextNode(
			id_=node_id or str(uuid.uuid4()),
			text=text,
			metadata={
				LOG_DATE_NAME: [date,],
				LOG_TIME_NAME: [h_m_s,],
				MEMORY_NODE_TYPE_NAME: node_type,
			}
		)
		node.excluded_embed_metadata_keys = [MEMORY_NODE_TYPE_NAME,]
		node.excluded_llm_metadata_keys = [MEMORY_NODE_TYPE_NAME, ]
		return node

	def put(self, experiment_name: str, log_str: str):
		r"""
		Put in an experiment log into a specific experiment store.

		These operations are done:

		- last_log_node -> set_next(new_log_node)
		- new_log_node -> set_previous(last_log_node)
		- last_store_node -> set_content(new_log_node.node_id)
		- experiment_node -> add_child(new_log_node)
		"""
		root_node = self._get_node(node_id=INIT_NODE_NAME)
		experiments = root_node.child_nodes
		if experiments is None or experiment_name not in [expr.node_id for expr in experiments]:
			raise ValueError(f"The experiment {experiment_name} of user {self.user_id} does not exist.")

		new_log_node = self._new_node(
			text=log_str,
			node_type=LOG_NODE_TYPE,
		)
		expr_node = self._get_node(node_id=experiment_name)
		last_store_name = f"{experiment_name}_{EXPERIMENT_LAST_NODE_ID_PREFIX}"
		last_store_node = self._get_node(node_id=last_store_name)
		last_log_id = last_store_node.text
		last_log_node = self._get_node(last_log_id)
		last_log_node.relationships[NodeRelationship.NEXT] = RelatedNodeInfo(
			node_id=new_log_node.node_id
		)
		new_log_node.relationships[NodeRelationship.PREVIOUS] = RelatedNodeInfo(
			node_id=last_log_node.node_id
		)
		new_log_node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(
			node_id=expr_node.node_id
		)
		last_store_node.set_content(new_log_node.node_id)
		self._update_node(node_id=last_log_id, node=last_log_node)
		self._update_node(node_id=last_store_name, node=last_store_node)

		log_node_list = expr_node.child_nodes or []
		log_node_list.append(
			RelatedNodeInfo(node_id=new_log_node.node_id)
		)
		expr_node.relationships[NodeRelationship.CHILD] = log_node_list
		self._update_node(node_id=experiment_name, node=expr_node)
		self.vector_index.insert_nodes([new_log_node])

	def persist(self, persist_dir: str = None):
		persist_dir = persist_dir or self.persist_dir
		fs = fsspec.filesystem("file")
		if not fs.exists(persist_dir):
			fs.makedirs(persist_dir)
		self.vector_index.storage_context.persist(persist_dir=persist_dir)


if __name__ == "__main__":
	# TODO: to be validated.
	llm, embed_model = get_models()
	expr_log = ExperimentLog.from_user_id(user_id="杨再正", embed_model=embed_model)
	print(expr_log.get_all_experiments())
	print(expr_log.is_expr_exist(experiment_name="强化学习优化忆阻器写入策略"))
	print(expr_log.get_expr_log_node_ids(experiment_name="强化学习优化忆阻器写入策略"))
	expr_log.set_recent_experiment(
		experiment_name="强化学习优化忆阻器写入策略",
		start_date="2024-08-15",
		start_time="09:13:00",
		end_date="2024-08-17",
		end_time="08:00:00"
	)
	print(expr_log.get_recent_experiment())
