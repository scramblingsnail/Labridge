import fsspec

from llama_index.core.indices import VectorStoreIndex
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core import load_index_from_storage
from llama_index.core.ingestion import run_transformations
from llama_index.core.storage import StorageContext
from llama_index.core.readers import SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import (
	TextNode,
	NodeRelationship,
	RelatedNodeInfo,
	BaseNode,
	TransformComponent,
)

from labridge.common.utils.time import get_time

from pathlib import Path
from typing import Dict, Any, List, Optional

from labridge.accounts.users import AccountManager


r"""
This file including the temporary paper info store that including the recent paper of each user.
Each index is attributed to a user.
"""


# a root node --> paper_node --> child --> paper_docs (including summary node)


TMP_PAPER_ROOT_NODE_NAME = "root_node"
TMP_PAPER_SUMMARY_NODE_PREFIX = "summary_node_"
TMP_PAPER_VECTOR_INDEX_ID = "temporary_paper_vector_index"
TMP_PAPER_VECTOR_INDEX_PERSIST_DIR = "storage/tmp_papers"
TMP_PAPER_WAREHOUSE_DIR = "documents/tmp_papers"

TMP_PAPER_DATE = "date"
TMP_PAPER_TIME = "time"

TMP_PAPER_FILE_PATH_KEY = "absolute_file_path"

TMP_PAPER_NODE_TYPE_KEY = "node_type"
TMP_PAPER_DOC_NODE_TYPE = "paper_doc_node"


def tmp_paper_get_file_metadata(file_path: str) -> Dict[str, Any]:
	r"""
	Record these metadata in each doc node:

	- the absolute file path of the paper.
	- the date when the file is put in.
	- the time when the file is put in.
	"""
	date, h_m_s = get_time()
	metadata = {
		TMP_PAPER_FILE_PATH_KEY: file_path,
		TMP_PAPER_DATE: [date,],
		TMP_PAPER_TIME: [h_m_s,],
	}
	return metadata


class RecentPaperStore(object):
	r"""
	This class stores the recent papers of a specific user.
	It is constructed as a tree, with a root node.

	Different papers are inserted as child nodes of the root node,
	the node_id is the absolute file path (in the recent paper warehouse) of the paper.

	For each paper node, TextNodes recording paper contents are stored as its child nodes.
	Like:

	```
											root_node
										/				\
									   /				 \
									Paper1					Paper2
							/		...				\
						node_1  					node_n
	```

	Args:
		vector_index (VectorStoreIndex): The vector database storing recent papers.
		persist_dir (persist_dir): The persist directory of the vector database.

	Note:
		The metadata `date` and `time` is recorded in a list format for the convenience of metadata filtering.
		For example: ['2024-08-10'], ['09:05:03'].
	"""
	def __init__(
		self,
		vector_index: VectorStoreIndex,
		persist_dir: str
	):
		self.vector_index = vector_index
		self.vector_index.set_index_id(TMP_PAPER_VECTOR_INDEX_ID)
		self.persist_dir = persist_dir
		self._user_id = self.user_id
		self._fs = fsspec.filesystem("file")

		root = Path(__file__)
		for idx in range(5):
			root = root.parent
		self._root = root

	@classmethod
	def from_storage(
		cls,
		persist_dir: str,
		embed_model: BaseEmbedding,
	):
		r"""
		Load from a existing storage.

		Args:
			persist_dir (str): The persist directory of the existing storage.
			embed_model (BaseEmbedding): The used embedding model.

		Returns:
			RecentPaperStore
		"""
		vector_storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
		vector_index = load_index_from_storage(
			storage_context=vector_storage_context,
			index_id=TMP_PAPER_VECTOR_INDEX_ID,
			embed_model=embed_model,
		)
		return cls(
			vector_index=vector_index,
			persist_dir=persist_dir,
		)

	@property
	def user_id(self) -> str:
		r""" Return the user_id of this RecentPaperStore """
		user_id = Path(self.persist_dir).relative_to(self._root / TMP_PAPER_VECTOR_INDEX_PERSIST_DIR)
		return str(user_id)

	@classmethod
	def from_user_id(
		cls,
		user_id: str,
		embed_model: BaseEmbedding,
	):
		r"""
		Construct from a user_id.
		If the corresponding persist_dir of the user does not exist, a new RecentPaperStore will be created for the user.

		Args:
			user_id (str): The user_id of a Lab member.
			embed_model (BaseEmbedding): The used embedding model.

		Returns:
			RecentPaperStore
		"""
		account_manager = AccountManager()

		if user_id not in account_manager.get_users():
			raise ValueError(f"Invalid user id: {user_id}.")

		root = Path(__file__)
		for idx in range(5):
			root = root.parent

		persist_dir = str(root / f"{TMP_PAPER_VECTOR_INDEX_PERSIST_DIR}/{user_id}")
		fs = fsspec.filesystem("file")
		if fs.exists(persist_dir):
			return cls.from_storage(
				persist_dir=persist_dir,
				embed_model=embed_model,
			)

		# root node
		root_node = TextNode(
			text=f"Root node for the temporary papers of {user_id}",
			id_=TMP_PAPER_ROOT_NODE_NAME,
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

	def _check_valid_paper(self, paper_file_path: str):
		r""" Check whether the paper path is valid. """
		if not self._fs.exists(paper_file_path):
			raise ValueError(f"{paper_file_path} is not a valid file path, it does not exist.")

		suffix = Path(paper_file_path).suffix
		if suffix != ".pdf":
			raise ValueError(f"Only support .pdf format.")

	def check_valid_paper(self, paper_file_path: str):
		r"""
		Check whether the paper path is valid or not.

		1. Whether the paper_file_path exists.
		2. Whether the suffix is `.pdf`.

		Args:
			paper_file_path (str): The paper path.

		Returns:
			None

		Raises:
			ValueError: If the paper_file_path is not valid.
		"""
		self._check_valid_paper(paper_file_path=paper_file_path)

	def _update_node(
		self,
		node_id: str,
		node: BaseNode,
	):
		r""" Update an existing node in vector index. """
		self.vector_index.delete_nodes([node_id])
		self.vector_index.insert_nodes([node])

	def _delete_nodes(self, node_ids: List[str]):
		r""" Delete a node from the vector index. """
		self.vector_index.delete_nodes(node_ids=node_ids)

	def _get_node(self, node_id: str) -> BaseNode:
		r""" Get a node from the vector index according to node_id. """
		return self.vector_index.docstore.get_node(node_id)

	def _get_nodes(self, node_ids: List[str]) -> List[BaseNode]:
		r""" Get nodes from the vector index according to node_ids. """
		return self.vector_index.docstore.get_nodes(node_ids)

	def _default_transformations(self) -> List[TransformComponent]:
		return [SentenceSplitter(chunk_size=1024, chunk_overlap=256, include_metadata=True), ]

	def file_exists(self, file_path: str) -> bool:
		r"""
		Judge whether a paper exists in the RecentPaperStore according to its filename.

		Args:
			file_path (str): The file path of the paper.

		Returns:
			bool: Whether the paper exist or not.
		"""
		file_name = Path(file_path).name
		user_dir = self._root / f"{TMP_PAPER_VECTOR_INDEX_PERSIST_DIR}/{self.user_id}"
		paper_file_path = str(user_dir / file_name)

		try:
			self._get_node(node_id=paper_file_path)
			return True
		except ValueError:
			return False

	def put(self, paper_file_path: str, extra_metadata: dict = None):
		r"""
		put a new paper into the vector index.

		Args:
			paper_file_path (str): The absolute path of the paper.
			extra_metadata (dict): Extra metadata of the paper.
				For example, if the paper is downloaded from arXiv,
				much structured information will be provided by the downloader.

		Returns:
			None
		"""
		try:
			self._check_valid_paper(paper_file_path=paper_file_path)
		except ValueError:
			return

		file_name = Path(paper_file_path).name
		user_dir = self._root / f"{TMP_PAPER_VECTOR_INDEX_PERSIST_DIR}/{self.user_id}"
		paper_file_path = str(user_dir / file_name)

		try:
			_ = self._get_node(node_id=paper_file_path)
			print(f"{paper_file_path} already exists in the temporary papers of user {self._user_id}.")
			return
		except ValueError:
			pass

		self._fs.cp(paper_file_path, str(user_dir))
		root_node = self._get_node(node_id=TMP_PAPER_ROOT_NODE_NAME)
		papers = root_node.child_nodes or []

		date, h_m_s = get_time()
		paper_node = TextNode(
			id_=paper_file_path,
			text=f"The paper {paper_file_path}",
			metadata={
				TMP_PAPER_DATE: [date,],
				TMP_PAPER_TIME: [h_m_s,],
			}
		)
		papers.append(RelatedNodeInfo(node_id=paper_node.node_id))
		root_node.relationships[NodeRelationship.CHILD] = papers
		self._update_node(node_id=TMP_PAPER_ROOT_NODE_NAME, node=root_node)

		# read the paper:
		reader = SimpleDirectoryReader(
			input_files=[paper_file_path],
			file_metadata=tmp_paper_get_file_metadata,
			filename_as_id=True,
		)
		documents = reader.load_data()

		for doc in documents:
			self.vector_index.docstore.set_document_hash(doc.get_doc_id(), doc.hash)

		doc_nodes = run_transformations(
			nodes=documents,
			transformations=self._default_transformations()
		)

		child_nodes = []
		for doc_node in doc_nodes:
			child_nodes.append(RelatedNodeInfo(node_id=doc_node.node_id))
			doc_node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(node_id=paper_node.node_id)
			new_metadata = {
				TMP_PAPER_NODE_TYPE_KEY: TMP_PAPER_DOC_NODE_TYPE,
				TMP_PAPER_DATE: [date],
				TMP_PAPER_TIME: [h_m_s],
			}
			if extra_metadata:
				new_metadata.update(extra_metadata)

			doc_node.metadata.update(new_metadata)
			doc_node.excluded_llm_metadata_keys.append(TMP_PAPER_NODE_TYPE_KEY)
			doc_node.excluded_embed_metadata_keys.append(TMP_PAPER_NODE_TYPE_KEY)

		paper_node.relationships[NodeRelationship.CHILD] = child_nodes
		nodes = doc_nodes + [paper_node]
		self.vector_index.insert_nodes(nodes=nodes)

	def get_summary_node(self, paper_file_path: str) -> Optional[BaseNode]:
		r"""
		Get the summary node of a paper.

		Args:
			paper_file_path (str): The file path of the paper, equally the node_id of the paper_node.

		Returns:
			Optional[BaseNode]: The summary node the paper. If it does not exist, return None.
		"""
		summary_id = f"{TMP_PAPER_SUMMARY_NODE_PREFIX}{paper_file_path}"
		try:
			summary_node = self._get_node(node_id=summary_id)
			return summary_node
		except Exception as e:
			print(f"Summary node of {paper_file_path} does not exist. {e}")
			return None

	def get_paper_node(self, paper_file_path: str) -> Optional[BaseNode]:
		r"""
		Get the paper_node of a paper.

		Args:
			paper_file_path (str): The file path of the paper, equally the node_id of the paper_node.

		Returns:
			Optional[BaseNode]: The paper node.

		Raises:
			ValueError: If the paper node does not exist.
		"""
		self._check_valid_paper(paper_file_path=paper_file_path)
		try:
			paper_node = self._get_node(node_id=paper_file_path)
			return paper_node
		except Exception:
			raise ValueError(f"{paper_file_path} does not exists in the temporary papers of user {self._user_id}.")

	def insert_summary_node(self, paper_file_path: str, summary_node: TextNode):
		self._check_valid_paper(paper_file_path=paper_file_path)
		paper_node = self.get_paper_node(paper_file_path=paper_file_path)

		summary_node.id_ = f"{TMP_PAPER_SUMMARY_NODE_PREFIX}{paper_file_path}"
		summary_node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(node_id=paper_node.node_id)

		paper_docs = paper_node.child_nodes
		paper_docs.append(
			RelatedNodeInfo(node_id=summary_node.node_id)
		)
		doc_node = self._get_node(node_id=paper_docs[0].node_id)
		summary_node.metadata.update(doc_node.metadata)

		paper_node.relationships[NodeRelationship.CHILD] = paper_docs
		self._update_node(node_id=paper_node.node_id, node=paper_node)
		self.vector_index.insert_nodes(nodes=[summary_node])

	def get_paper_nodes(self, paper_file_path: str) -> Optional[List[BaseNode]]:
		r"""
		Get the doc nodes of a paper.

		Args:
			paper_file_path (str): The file path of the paper, equally the node_id of the paper_node.

		Returns:
			Optional[List[BaseNode]]: The doc nodes of the paper.

		Raises:
			ValueError: If the paper does not exist.

		"""
		self._check_valid_paper(paper_file_path=paper_file_path)
		paper_node = self.get_paper_node(paper_file_path=paper_file_path)
		doc_nodes = paper_node.child_nodes
		doc_ids = [node.node_id for node in doc_nodes]
		paper_nodes = self._get_nodes(node_ids=doc_ids)
		return paper_nodes

	def get_all_relevant_node_ids(self, node_ids: List[str]) -> Optional[List[str]]:
		r"""
		Get all the ids of the nodes that are belong to the same papers with the input node_ids.

		Args:
			node_ids (List[str]): The node ids.

		Returns:
			Optional[List[str]]: The relevant doc nodes. If no relevant node exists, return None.
		"""
		paper_ids = set()
		for node_id in node_ids:
			try:
				node = self._get_node(node_id=node_id)
				paper_id = node.parent_node.node_id
				paper_ids.add(paper_id)
			except Exception:
				continue
		if len(paper_ids) < 1:
			return None

		all_ids = []
		for paper_id in paper_ids:
			paper_nodes = self.get_paper_nodes(paper_file_path=paper_id)
			all_ids.extend([node.node_id for node in paper_nodes])
		return all_ids

	def delete(self, paper_file_path: str):
		r"""
		Delete a paper from the recent paper vector index and the recent paper warehouse.

		Args:
			paper_file_path (str): The file path of the paper, equally the node_id of the paper_node.
		"""
		self._check_valid_paper(paper_file_path=paper_file_path)
		paper_node = self.get_paper_node(paper_file_path=paper_file_path)
		doc_nodes = paper_node.child_nodes
		delete_ids = [paper_node.node_id]
		delete_ids.extend([doc_node.node_id for doc_node in doc_nodes])
		self._delete_nodes(node_ids=delete_ids)

		root_node = self._get_node(node_id=TMP_PAPER_ROOT_NODE_NAME)
		papers = root_node.child_nodes
		for paper in papers:
			if paper.node_id == paper_file_path:
				papers.remove(paper)
		root_node.relationships[NodeRelationship.CHILD] = papers
		self._update_node(node_id=TMP_PAPER_ROOT_NODE_NAME, node=root_node)
		if Path(paper_file_path).is_relative_to(TMP_PAPER_WAREHOUSE_DIR):
			self._fs.rm(paper_file_path)

	def persist(self, persist_dir: str = None):
		r"""
		Persis to the disk.

		Args:
			persist_dir (str): The save directory. Defaults to `self.persist_dir`
		"""
		persist_dir = persist_dir or self.persist_dir
		if not self._fs.exists(persist_dir):
			self._fs.makedirs(persist_dir)
		self.vector_index.storage_context.persist(persist_dir=persist_dir)
