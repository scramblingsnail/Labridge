import fsspec
import uuid

from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core import load_index_from_storage
from llama_index.core.storage import StorageContext
from llama_index.core.bridge.pydantic import Field
from llama_index.core import Settings
from llama_index.core.schema import (
	TextNode,
	NodeRelationship,
	RelatedNodeInfo,
	BaseNode,
	MetadataMode,
)
from llama_index.core.base.llms.types import (
	ChatMessage,
	MessageRole,
)

from pathlib import Path

from labridge.accounts.users import AccountManager
from labridge.common.chat.utils import get_time
from labridge.llm.models import get_models
from labridge.callback.experiment_note import *



EXPERIMENT_LOG_PERSIST_DIR = "storage/experiment_log"
EXPERIMENT_LOG_VECTOR_INDEX_ID = "experiment_log"
LOG_DATE_NAME = "date"
LOG_TIME_NAME = "time"
EXPERIMENT_INSTRUMENT_NAME = "instruments"

INIT_NODE_NAME = "root_node"
RECENT_EXPERIMENT_NODE_NAME = "recent_experiment"
EXPERIMENT_LAST_NODE_ID_PREFIX = "last_log"



class ExperimentLog(object):
	r"""
	User --> Experiment (description) --> time (child nodes)

	Experiment: relevant instruments. --> Instrument ID

	Types: User_Node: content: all the experiment name,

	experiment log,
	experiment note,

	Log is user by user, Note is all in one.

	A Node for each user: store the e

	retrieve 1: global similarity retrieve.
	retrieve 2: confine the user, experiment, instrument.

	default retrieve: retrieve among the current experiment name.

	user give experiment:
		1. match the experiment (according to the experiment description.)

	For each default query, check whether is valid time, if not valid, ask the user.
	ask the user which experiment is working, and the start time and end time.
	record as recent experiment name.

	Update the log index: insert as a child node.
	Delete recent ID
	"""
	def __init__(self, vector_index: VectorStoreIndex, persist_dir: str):
		self.vector_index = vector_index
		self.persist_dir = persist_dir

	@classmethod
	def from_storage(
		cls,
		persist_dir: str,
		embed_model: BaseEmbedding
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
		root = Path(__file__)
		for idx in range(4):
			root = root.parent

		user_id = Path(self.persist_dir).relative_to(root / EXPERIMENT_LOG_PERSIST_DIR)
		return str(user_id)

	@classmethod
	def from_user_id(
		cls,
		user_id: str,
		embed_model: BaseEmbedding,
	):
		account_manager = AccountManager()

		if user_id not in account_manager.get_users():
			raise ValueError(f"Invalid user id: {user_id}.")

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

		# root node
		root_node = TextNode(
			text=f"Root node for the experiment logs of {user_id}",
			id_=INIT_NODE_NAME,
		)
		nodes = [root_node]
		vector_index = VectorStoreIndex(
			nodes=nodes,
			embed_model=embed_model,
		)
		return cls(
			vector_index=vector_index,
			persist_dir=persist_dir,
		)

	def _get_node(self, node_id: str) -> BaseNode:
		return self.vector_index._docstore.get_node(node_id)

	def _update_node(
		self,
		node_id: str,
		node: BaseNode,
	):
		self.vector_index.delete_nodes([node_id])
		self.vector_index.insert_nodes([node])

	def create_experiment(self, experiment_name: str, description: str):
		root_node = self._get_node(node_id=INIT_NODE_NAME)
		expr_list = root_node.relationships[NodeRelationship.CHILD]
		if experiment_name in [expr.node_id for expr in expr_list]:
			raise ValueError(f"The experiment name {experiment_name} already exists.")

		new_expr_node = TextNode(
			id_=experiment_name,
			text=description,
			metadata={
				EXPERIMENT_INSTRUMENT_NAME: [],
			},
		)

		expr_header_node = TextNode(
			id_=f"{experiment_name}_header",
			text=f"The log beginning of the experiment {experiment_name}",
		)

		last_info_node = TextNode(
			id_=f"{experiment_name}_{EXPERIMENT_LAST_NODE_ID_PREFIX}",
			text=expr_header_node.node_id,
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

	def put(self, experiment_name: str, log_str: str):
		root_node = self._get_node(node_id=INIT_NODE_NAME)
		experiments = root_node.child_nodes
		if experiments is None or experiment_name not in [expr.node_id for expr in experiments]:
			raise ValueError(f"The experiment {experiment_name} of user {self.user_id} do not exist.")

		date, h_m_s = get_time()
		new_log_node = TextNode(
			id_=str(uuid.uuid4()),
			text=log_str,
			metadata={
				LOG_DATE_NAME: date,
				LOG_TIME_NAME: h_m_s,
			},
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
		last_store_node.set_content(new_log_node.node_id)
		self._update_node(node_id=last_log_id, node=last_log_node)
		self._update_node(node_id=last_store_name, node=last_log_node)

		log_node_list = expr_node.relationships[NodeRelationship.CHILD]
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
