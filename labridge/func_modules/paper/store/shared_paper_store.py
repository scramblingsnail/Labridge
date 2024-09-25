r"""
Shared paper storage.

A Tree-type storage.

With members as the first child nodes. (Member Node type)

Then recursive DIR nodes, corresponding to the warehouse's dir. (DIR node type)

The leaf nodes: paper node. (include summary, abstraction, metadata, Title, ref_filepath) (Paper node type)

The child nodes of paper node: doc nodes. () (with overlap) (Doc node type)

Another child nodes of paper node: doc nodes for note. (without overlap, more detailed.) (Note Doc node type).

Notes: The note of the corresponding context. (Note node type.)
"""

import fsspec
import json

from llama_index.core.indices import VectorStoreIndex
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core import load_index_from_storage
from llama_index.core.ingestion import run_transformations
from llama_index.core.storage import StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.response import Response
from llama_index.core.llms import LLM
from llama_index.core import Settings
from llama_index.core.readers import SimpleDirectoryReader
from llama_index.core.vector_stores.types import (
	MetadataFilters,
	MetadataFilter,
	FilterOperator,
)
from llama_index.core.schema import (
	TextNode,
	NodeRelationship,
	RelatedNodeInfo,
	BaseNode,
	TransformComponent,
	NodeWithScore,
	MetadataMode,
)

from pathlib import Path
from collections import defaultdict
from typing import Dict, Any, List, Optional, Tuple, cast

from labridge.accounts.users import AccountManager
from labridge.common.utils.time import get_time, str_to_datetime
from labridge.func_modules.paper.parse.extractors.metadata_extract import PAPER_REL_FILE_PATH, PAPER_DOI
from labridge.func_modules.paper.parse.paper_reader import PaperReader, SHARED_PAPER_WAREHOUSE_DIR
from labridge.func_modules.paper.parse.parsers.base import CONTENT_TYPE_NAME
from labridge.func_modules.paper.synthesizer.summarize import PaperBatchSummarize


SHARED_PAPER_VECTOR_INDEX_ID = "shared_paper_vector_index"
SHARED_PAPER_VECTOR_INDEX_PERSIST_DIR = "storage/shared_papers/vector_index"

SHARED_PAPER_NOTES_INDEX_ID = "shared_paper_notes_index"
SHARED_PAPER_NOTES_INDEX_PERSIST_DIR = "storage/shared_papers/notes_vector_index"

SHARED_PAPER_ROOT_NODE_NAME = "root_node"
SHARED_PAPER_NODE_TYPE = "node_type"

SHARED_PAPER_SUMMARY_KEY = "summary"
SHARED_PAPER_DOI_KEY = "paper_doi"

SHARED_PAPER_PAGE_LABEL_KEY = "page_label"
SHARED_PAPER_TOTAL_PAGES_KEY = "total_pages"

SHARED_PAPER_CHUNK_INIT_NOTE_KEY = "init_note_id"
SHARED_PAPER_CHUNK_LAST_NOTE_KEY = "last_note_id"

SHARED_NOTE_DATE_KEY = "date"
SHARED_NOTE_TIME_KEY = "time"


class SharedPaperNodeType(object):
	ROOT = "root_node"
	USER = "user_node"
	DIR = "dir_node"
	PAPER = "paper_node"
	PAPER_CHUNK = "chunk_node"
	PAPER_CHUNK_FOR_NOTE = "chunk_for_note_node"
	PAPER_EXTRA_INFO = "paper_extra_info_node"


class SharedPaperNoteNodeType(object):
	ROOT = "root_node"
	DOI = "doi_node"
	PAPER_CHUNK = "chunk_node"
	NOTE = "note_node"


class MarkAsChunk(TransformComponent):
	r"""
	A TransformComponent to mark the node type of each node of the vector index as `chunk_node`.
	"""

	def __call__(self, nodes: List["BaseNode"], **kwargs: Any) -> List["BaseNode"]:
		for node in nodes:
			node.metadata[SHARED_PAPER_NODE_TYPE] = SharedPaperNodeType.PAPER_CHUNK
		return nodes


class MarkAsChunkForNote(TransformComponent):
	r"""
	A TransformComponent to mark the node type of each node of the notes vector index as `chunk_node`.
	"""

	def __call__(self, nodes: List["BaseNode"], **kwargs: Any) -> List["BaseNode"]:
		for node in nodes:
			node.metadata[SHARED_PAPER_NODE_TYPE] = SharedPaperNoteNodeType.PAPER_CHUNK
			node.metadata[SHARED_PAPER_CHUNK_INIT_NOTE_KEY] = None
			node.metadata[SHARED_PAPER_CHUNK_LAST_NOTE_KEY] = None
		return nodes


class UserNote(object):
	def __init__(
		self,
		doi: str,
		user_id: str,
		note: str,
		date_str: str = None,
		time_str: str = None,
		timestamp: str = None,
	):
		self.doi = doi
		self.user_id = user_id
		self.note = note
		if timestamp is None and None in (date_str, time_str):
			raise ValueError("timestamp and (date_str, time_str) cannot both be None.")

		self.timestamp = timestamp or f"{date_str} {time_str}"

	def dumps(self) -> str:
		class_dict = {
			"doi": self.doi,
			"user_id": self.user_id,
			"note": self.note,
			"timestamp": self.timestamp,
		}
		return json.dumps(class_dict)

	@classmethod
	def loads(cls, dumped_str: str):
		class_dict = json.loads(dumped_str)
		return cls(
			doi=class_dict["doi"],
			user_id=class_dict["user_id"],
			note=class_dict["note"],
			timestamp=class_dict["timestamp"],
		)


class ChunkNote(object):
	def __init__(
		self,
		doi: str,
		page_label: int,
		chunk_content: str,
		notes: List[UserNote],
	):
		self.doi = doi
		self.page_label = page_label
		self.chunk_content = chunk_content
		self.notes = notes

	def dumps(self) -> str:
		dumped_notes = [user_note.dumps() for user_note in self.notes]
		class_dict = {
			"doi": self.doi,
			"page_label": self.page_label,
			"chunk_content": self.chunk_content,
			"notes": json.dumps(dumped_notes),
		}
		return json.dumps(class_dict)

	@classmethod
	def loads(cls, dumped_str):
		class_dict = json.loads(dumped_str)
		dumped_notes = json.loads(class_dict["notes"])
		notes = [UserNote.loads(note_str) for note_str in dumped_notes]
		return cls(
			doi=class_dict["doi"],
			page_label=class_dict["page_label"],
			chunk_content=class_dict["chunk_content"],
			notes=notes,
		)


def dummy_file_metadata_func(file_path: str) -> Dict:
	return {}


class SharedPaperStorage(object):
	r"""
	This class is for storing shared papers and notes.
	Two vector databases are used for storage:

	- Paper vector index: This vector database records the overlapped paper content chunks along with detailed metadata.
	This database is structured the same as the directory structure of the shared paper warehouse. For example:

	```
												root_node
							/				/				\			\
						user_1			user_2		...		user_m		user_n
					/			\
				dir_1_1		...	dir_1_k
				/				/
			dir_2_1		...	Paper_1
			/	\			/	\
		Paper_1	Paper_p	Chunk_1	Chunk_l
		/	\
	Chunk_1	Chunk_l
	```
	- Notes vector index: This vector database non-overlapped content chunks of smaller size and corresponding user notes.
	Each paper uses its DOI as the sign. This database is structured as follows:

	```
												root_node
						/					/				\					\
					DOI_1				DOI_2				DOI_m				DOI_n
				/			\												/			\
			Chunk_1			Chunk_k										Chunk_1			Chunk_k
		/			\																/			\
	Note_1			Note_l														Note_1			Note_l
	```

	The `PaperReader` is used to parse content and metadata from the paper pdf.

	Note:
		the metadata `Title` and `DOI` is essential. The `Title` is extracted by LLM, and the `DOI` is obtained through
	CrossRef API according to the extracted `Title`. If any of the two fails in extraction, the paper recording fails.

	Args:
		llm (LLM): The used LLM
		vector_index (VectorStoreIndex): The vector database for storing shared paper contents.
		notes_vector_index (VectorStoreIndex): The vector database fot storing non-overlapped paper content chunks and
			their corresponding user notes.
		persist_dir (str): The persist directory of the vector_index.
		notes_persist_dir (str): The persist directory of the notes_vector_index.
	"""
	def __init__(
		self,
		llm: LLM,
		vector_index: VectorStoreIndex,
		notes_vector_index: VectorStoreIndex,
		persist_dir: str,
		notes_persist_dir: str,
	):
		root = Path(__file__)
		for idx in range(5):
			root = root.parent
		self._root = root
		self.vector_index = vector_index
		self.vector_index.set_index_id(index_id=SHARED_PAPER_VECTOR_INDEX_ID)
		self.notes_vector_index = notes_vector_index
		self.notes_vector_index.set_index_id(index_id=SHARED_PAPER_NOTES_INDEX_ID)
		self.vector_index.set_index_id(SHARED_PAPER_VECTOR_INDEX_ID)
		self.persist_dir = persist_dir
		self.notes_persist_dir = notes_persist_dir
		self._fs = fsspec.filesystem("file")
		self._account_manager = AccountManager()
		self.paper_reader = PaperReader(llm=llm)
		self._summarizer = PaperBatchSummarize(llm=llm)

	@classmethod
	def from_storage(
		cls,
		persist_dir: str,
		notes_persist_dir: str,
		llm: LLM,
		embed_model: BaseEmbedding,
	):
		vector_storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
		vector_index = load_index_from_storage(
			storage_context=vector_storage_context,
			index_id=SHARED_PAPER_VECTOR_INDEX_ID,
			embed_model=embed_model,
		)
		notes_storage_context = StorageContext.from_defaults(persist_dir=notes_persist_dir)
		notes_vector_index = load_index_from_storage(
			storage_context=notes_storage_context,
			index_id=SHARED_PAPER_NOTES_INDEX_ID,
			embed_model=embed_model,
		)
		return cls(
			llm=llm,
			vector_index=vector_index,
			notes_vector_index=notes_vector_index,
			persist_dir=persist_dir,
			notes_persist_dir=notes_persist_dir,
		)

	@classmethod
	def from_default(
		cls,
		llm: LLM,
		embed_model: BaseEmbedding,
	):
		root = Path(__file__)
		for idx in range(5):
			root = root.parent

		persist_dir = str(root / SHARED_PAPER_VECTOR_INDEX_PERSIST_DIR)
		notes_persist_dir = str(root / SHARED_PAPER_NOTES_INDEX_PERSIST_DIR)
		fs = fsspec.filesystem("file")
		if fs.exists(persist_dir):
			return cls.from_storage(
				persist_dir=persist_dir,
				notes_persist_dir=notes_persist_dir,
				llm=llm,
				embed_model=embed_model,
			)

		root_node = TextNode(
			text=f"Root node for the shared papers",
			id_=SHARED_PAPER_ROOT_NODE_NAME,
			metadata={
				SHARED_PAPER_NODE_TYPE: SharedPaperNodeType.ROOT,
			}
		)
		nodes = [root_node]

		account_manager = AccountManager()
		users = account_manager.get_users()

		root_children = []
		for user_id in users:
			user_node = TextNode(
				text=f"The papers belonging to the user {user_id}",
				id_=user_id,
				metadata={
					SHARED_PAPER_NODE_TYPE: SharedPaperNodeType.USER,
				}
			)
			nodes.append(user_node)
			root_children.append(RelatedNodeInfo(node_id=user_node.node_id))
			user_node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(node_id=root_node.node_id)

		root_node.relationships[NodeRelationship.CHILD] = root_children

		vector_index = VectorStoreIndex(
			nodes=nodes,
			embed_model=embed_model,
		)

		notes_root_node = TextNode(
			text="Root node for the paper notes.",
			id_=SHARED_PAPER_ROOT_NODE_NAME,
			metadata={
				SHARED_PAPER_NODE_TYPE: SharedPaperNoteNodeType.ROOT,
			}
		)
		notes_vector_index = VectorStoreIndex(
			nodes=[notes_root_node],
			embed_model=embed_model,
		)

		return cls(
			llm=llm,
			vector_index=vector_index,
			notes_vector_index=notes_vector_index,
			persist_dir=persist_dir,
			notes_persist_dir=notes_persist_dir,
		)

	@property
	def _default_overlapped_transformations(self):
		r""" Transformations for chunks in vector_index """
		return [SentenceSplitter(chunk_size=1024, chunk_overlap=256, include_metadata=True), MarkAsChunk()]

	@property
	def _default_non_overlapped_transformations(self):
		r""" Transformation for chunks in notes_vector_index """
		return [SentenceSplitter(chunk_size=128, chunk_overlap=0, include_metadata=True), MarkAsChunkForNote()]

	def _update_node(self, node_id: str, node: BaseNode):
		r""" Update a node in the vector_index, if the node with `node_id` does not exist, create one. """
		try:
			self.vector_index.delete_nodes([node_id])
		except:
			pass
		self.vector_index.insert_nodes([node])

	def _update_note_index_node(self, node_id: str, node: BaseNode):
		r""" Update a node in the notes_vector_index, if the node with `node_id` does not exist, create one. """
		try:
			self.notes_vector_index.delete_nodes([node_id])
		except:
			pass
		self.notes_vector_index.insert_nodes([node])

	def _get_node(self, node_id: str) -> Optional[BaseNode]:
		r""" Get node from the vector_index. """
		try:
			node = self.vector_index.docstore.get_node(node_id=node_id, raise_error=True)
			return node
		except ValueError:
			return None

	def _get_nodes(self, node_ids: List[str], node_types: List[str] = None) -> List[BaseNode]:
		r"""
		Get nodes from the vector_index, with optional node type filters.

		Args:
			node_ids (List[str]): The ids of the nodes to be obtained.
			node_types (List[str]): If given, only nodes with types in the given node_types will be selected.

		Returns:
			The corresponding nodes.
		"""
		nodes = self.vector_index.docstore.get_nodes(node_ids=node_ids, raise_error=True)
		if node_types is not None:
			nodes = [n for n in nodes if n.metadata[SHARED_PAPER_NODE_TYPE] in node_types]
		return nodes

	def _get_notes_index_node(self, node_id: str) -> Optional[BaseNode]:
		r""" Get node from the notes vector index. """
		try:
			node = self.notes_vector_index.docstore.get_node(node_id=node_id, raise_error=True)
			return node
		except ValueError:
			return None

	def _new_dir_node(self, rel_dir_path: str) -> TextNode:
		r""" Create a new DIR node in the vector_index. """
		dir_node = TextNode(
			text=f"The directory of {rel_dir_path}",
			id_=rel_dir_path,
			metadata={
				SHARED_PAPER_NODE_TYPE: SharedPaperNodeType.DIR,
			}
		)
		return dir_node

	def _insert_as_child_nodes(self, node: BaseNode, child_nodes: List[BaseNode]):
		r"""
		Set the child_nodes of the given node, and set the node as the PARENT of each child node in the child_nodes.

		Args:
			node (BaseNode): The parent node.
			child_nodes (List[BaseNode]): The child nodes.

		Returns:
			None
		"""
		children = node.child_nodes or []
		for child in child_nodes:
			children.append(
				RelatedNodeInfo(node_id=child.node_id)
			)
			child.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(
				node_id=node.node_id
			)
		node.relationships[NodeRelationship.CHILD] = children

	def _new_paper_node(self, dir_node: BaseNode, paper_info: dict) -> Tuple[BaseNode, BaseNode]:
		r"""
		Create a paper node under the given dir_node. Use rel_path as node_id.

		Args:
			dir_node (BaseNode): The dir_node indicating a specific directory in the paper warehouse.
			paper_info (dict): The metadata of the info. `PAPER_REL_FILE_PATH` is necessary.

		Returns:
			The updated dir_node and the created paper_node.

		Raises:
			ValueError: If `PAPER_REL_FILE_PATH` is not given in the paper_info.
		"""
		paper_rel_path = paper_info.get(PAPER_REL_FILE_PATH, None)
		if paper_rel_path is None:
			raise ValueError(f"Invalid paper metadata, the key: {PAPER_REL_FILE_PATH} is needed.")

		metadata = {
			SHARED_PAPER_NODE_TYPE: SharedPaperNodeType.PAPER,
		}
		metadata.update(paper_info)

		paper_node = TextNode(
			text="",
			id_=paper_rel_path,
			metadata=metadata,
		)
		self._insert_as_child_nodes(node=dir_node, child_nodes=[paper_node])
		return dir_node, paper_node

	def _new_doi_node(self, doi: str) -> BaseNode:
		r"""
		Create a new DOI node in the notes vector index, as the child of the root node.

		Args:
			doi (str): The DOI of a paper.

		Returns:
			The created DOI node.
		"""
		metadata = {
			SHARED_PAPER_NODE_TYPE: SharedPaperNoteNodeType.DOI,
		}
		doi_node = TextNode(
			text=f"DOI: {doi}",
			id_=doi,
			metadata=metadata,
		)

		note_root_node = self._get_notes_index_node(node_id=SHARED_PAPER_ROOT_NODE_NAME)
		self._insert_as_child_nodes(node=note_root_node, child_nodes=[doi_node, ])
		self._update_note_index_node(node_id=note_root_node.node_id, node=note_root_node)
		return doi_node

	def _new_note_node(self, user_id: str, note: str) -> BaseNode:
		r""" Create a new note node. """
		date, h_m_s = get_time()
		node = TextNode(
			text=note,
			metadata={
				SHARED_PAPER_NODE_TYPE: SharedPaperNoteNodeType.NOTE,
				"user_id": user_id,
				SHARED_NOTE_DATE_KEY: [date, ],
				SHARED_NOTE_TIME_KEY: [h_m_s, ],
			}
		)
		return node

	def _is_valid_paper_dir(self, rel_dir: str) -> bool:
		r""" Only when the relative dir path is under the `SHARED_PAPER_WAREHOUSE_DIR`, it is valid. """
		try:
			Path(rel_dir).relative_to(SHARED_PAPER_WAREHOUSE_DIR)
			return True
		except ValueError:
			return False

	def make_dirs(self, rel_dir: str):
		r"""
		Recursively add DIR nodes for a rel_dir.

		relative path to what? match the old vector index.

		Args:
			rel_dir (str): The path of a directory relative to the root.

		Returns:
			None

		Raises:
			ValueError: If the given rel_dir is not valid, that is, the rel_dir is not under the `SHARED_PAPER_WAREHOUSE_DIR`.

		"""
		if not self._is_valid_paper_dir(rel_dir=rel_dir):
			raise ValueError(f"The directory {rel_dir} is not under the warehouse {SHARED_PAPER_WAREHOUSE_DIR}.")

		path_parts = Path(rel_dir).relative_to(SHARED_PAPER_WAREHOUSE_DIR).parts
		assert len(path_parts) > 1

		user_id = path_parts[0]
		self._account_manager.check_valid_user(user_id=user_id)
		user_node = self._get_node(node_id=user_id) or self.add_user_node(user_id=user_id)
		dir_path = Path(SHARED_PAPER_WAREHOUSE_DIR) / user_id
		# [node, whether to update]
		dirs_nodes = [[user_node, False]]

		for part in path_parts[1:]:
			dir_path = dir_path / part
			dir_node = self._get_node(node_id=str(dir_path))
			if_new_dir = dir_node is None
			if if_new_dir:
				dir_node = self._new_dir_node(rel_dir_path=str(dir_path))
				parent_node = dirs_nodes[-1][0]
				dirs_nodes[-1][1] = True
				dir_node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(
					node_id=parent_node.node_id,
				)
				self._insert_as_child_nodes(node=parent_node, child_nodes=[dir_node])
			dirs_nodes.append([dir_node, if_new_dir])

		to_update_nodes = [pair[0] for pair in dirs_nodes if pair[1]]
		for node in to_update_nodes:
			self._update_node(node_id=node.node_id, node=node)

	def summarize_paper(self, paper_node_id: str) -> Optional[str]:
		r"""
		Summarize a paper in the shared paper storage.

		Args:
			paper_node_id (str): The node id of the corresponding paper node.

		Returns:
			Optional[str]: The summary of th paper. If the paper does not exist, return None.
		"""
		paper_node = self._get_node(node_id=paper_node_id)
		if paper_node is None:
			return None

		summary = paper_node.metadata.get(SHARED_PAPER_SUMMARY_KEY, None)
		if summary is not None:
			return summary

		content_ids = [child.node_id for child in paper_node.child_nodes]
		content_nodes = self._get_nodes(
			node_ids=content_ids,
			node_types=[SharedPaperNodeType.PAPER_CHUNK]
		)

		nodes_with_scores = [NodeWithScore(node=n) for n in content_nodes]
		# get the summary for each doc_id
		summary_response = self._summarizer.synthesize(nodes=nodes_with_scores, query="")
		summary_response = cast(Response, summary_response)
		summary = summary_response.response
		paper_node.metadata[SHARED_PAPER_SUMMARY_KEY] = summary
		self._update_node(node_id=paper_node.node_id, node=paper_node)
		return summary

	async def asummarize_paper(self, paper_node_id: str) -> Optional[str]:
		r"""
		Asynchronously summarize a paper in the shared paper storage.

		Args:
			paper_node_id (str): The node id of the corresponding paper node.

		Returns:
			Optional[str]: The summary of th paper. If the paper does not exist, return None.
		"""
		paper_node = self._get_node(node_id=paper_node_id)
		if paper_node is None:
			return None

		summary = paper_node.metadata.get(SHARED_PAPER_SUMMARY_KEY, None)
		if summary is not None:
			return summary

		content_ids = [child.node_id for child in paper_node.child_nodes]
		content_nodes = self._get_nodes(
			node_ids=content_ids,
			node_types=[SharedPaperNodeType.PAPER_CHUNK]
		)

		nodes_with_scores = [NodeWithScore(node=n) for n in content_nodes]
		# get the summary for each doc_id
		summary_response = await self._summarizer.asynthesize(nodes=nodes_with_scores, query="")
		summary_response = cast(Response, summary_response)
		summary = summary_response.response
		paper_node.metadata[SHARED_PAPER_SUMMARY_KEY] = summary
		self._update_node(node_id=paper_node.node_id, node=paper_node)
		return summary

	def insert_single_paper(
		self,
		target_rel_dir: str,
		raw_paper_path: str,
		paper_summary: str = None,
		extra_metadata: dict = None,
	) -> Optional[str]:
		r"""
		Add a paper to the shared paper storage.

		Args:
			target_rel_dir (str): The directory into which the new paper is inserted.
			raw_paper_path (str): The file path of the paper.
			paper_summary (str): If the paper has been summarized before, the summary can be provided to save cost.
			extra_metadata (dict): Extra metadata obtained from other approaches such as ArXiv.

		Returns:
			Optional[str]: The node id of the new paper node.
				Return None in these situation:

				- The target_rel_dir is not valid.
				- The raw_paper_path does not exist.
				- The given paper is not in pdf format.
				- The PaperReader fails to read the paper.
		"""
		# Deal with target dir
		if not self._is_valid_paper_dir(rel_dir=target_rel_dir):
			print("Invalid paper dir.")
			return None

		if not self._fs.exists(raw_paper_path):
			print("paper not exists.")
			return None

		paper_name = Path(raw_paper_path).name
		if Path(raw_paper_path).suffix != ".pdf":
			print("is not pdf.")
			return None

		target_dir = self._root / target_rel_dir
		paper_path = str(target_dir / paper_name)
		target_dir = str(target_dir)

		if not self._fs.exists(target_dir):
			self._fs.mkdirs(target_dir)

		# Move the paper to the warehouse.
		if paper_path != raw_paper_path:
			self._fs.cp(raw_paper_path, target_dir)

		read_content = self.paper_reader.read_single_paper(
			file_path=paper_path,
			extra_metadata=extra_metadata,
		)
		if read_content is None:
			return None

		chunk_docs, extra_docs = read_content
		dir_node = self._get_node(node_id=target_rel_dir)
		if dir_node is None:
			self.make_dirs(rel_dir=target_rel_dir)
			dir_node = self._get_node(node_id=target_rel_dir)

		paper_metadata = {
			key: chunk_docs[0].metadata[key] for key in chunk_docs[0].metadata.keys() if key != CONTENT_TYPE_NAME
		}
		if paper_summary:
			paper_metadata[SHARED_PAPER_SUMMARY_KEY] = paper_summary
		dir_node, paper_node = self._new_paper_node(dir_node=dir_node, paper_info=paper_metadata)
		self._update_node(node_id=dir_node.node_id, node=dir_node)

		# for doc in chunk_docs:
		# 	# TODO: check whether useful for break the warning that metadata str is longer than chunk content.
		# 	all_metadata_keys = list(doc.metadata.keys())
		# 	doc.excluded_embed_metadata_keys = []
		# 	doc.excluded_llm_metadata_keys = all_metadata_keys
		# overlapped nodes
		overlapped_chunk_nodes = run_transformations(
			nodes=chunk_docs,
			transformations=self._default_overlapped_transformations,
		)
		print("chunk node metadata: \n", overlapped_chunk_nodes[0].metadata)
		self._insert_as_child_nodes(node=paper_node, child_nodes=overlapped_chunk_nodes)
		for chunk_node in overlapped_chunk_nodes:
			self._update_node(node_id=chunk_node.node_id, node=chunk_node)

		# extra docs
		self._insert_as_child_nodes(node=paper_node, child_nodes=extra_docs)
		for doc in extra_docs:
			doc.metadata[SHARED_PAPER_NODE_TYPE] = SharedPaperNodeType.PAPER_EXTRA_INFO
			self._update_node(node_id=doc.node_id, node=doc)

		self._update_node(node_id=paper_node.node_id, node=paper_node)

		paper_doi = paper_metadata[PAPER_DOI]
		self.insert_doi_node(paper_doi=paper_doi, paper_path=paper_path)
		return paper_node.node_id

	def insert_doi_node(
		self,
		paper_doi: str,
		paper_path: str,
	) -> Optional[BaseNode]:
		r"""
		Insert a DOI node and its corresponding chunk nodes as children into the note index.

		Args:
			paper_doi (str): The DOI of a paper.
			paper_path (str): The paper path.

		Returns:
			Optional[BaseNode]: If the DOI node already exists or is successfully created, return the DOI node.
				If fails, return None.
		"""
		existing_node = self._get_notes_index_node(node_id=paper_doi)
		if existing_node:
			return existing_node

		try:
			paper_docs = SimpleDirectoryReader.load_file(
				input_file=Path(paper_path),
				file_extractor={},
				file_metadata=dummy_file_metadata_func,
			)
		except:
			return None

		# insert non-overlapped nodes to notes_index as child nodes of doi node.
		doi_node = self._new_doi_node(doi=paper_doi)

		pages_num = len(paper_docs)
		for doc in paper_docs:
			doc.metadata = {
				SHARED_PAPER_PAGE_LABEL_KEY: doc.metadata[SHARED_PAPER_PAGE_LABEL_KEY],
				SHARED_PAPER_TOTAL_PAGES_KEY: pages_num,
			}
		non_overlapped_chunk_nodes = run_transformations(
			nodes=paper_docs,
			transformations=self._default_non_overlapped_transformations,
		)

		self._insert_as_child_nodes(node=doi_node, child_nodes=non_overlapped_chunk_nodes)
		for chunk_node in non_overlapped_chunk_nodes:
			self._update_note_index_node(node_id=chunk_node.node_id, node=chunk_node)
		self._update_note_index_node(node_id=doi_node.node_id, node=doi_node)
		return doi_node

	def insert_papers(
		self,
		user_id: str,
		papers_root_dir: str,
		paper_paths: List[str],
		enable_summarize: bool
	) -> Optional[List[str]]:
		r"""
		Insert papers of a user.

		Args:
			user_id (str): The user id of a laboratory member.
			papers_root_dir (str): The raw root directory of these papers,
				the directory structure will be copied to the shared paper warehouse.
			paper_paths (List[str]): The paths of the papers.
			enable_summarize (bool): Whether to summarize these papers.

		Returns:
			Optional[List[str]]: The paths of failed papers. If no paper fails in recording, return None.
		"""

		target_dirs = []
		for paper_path in paper_paths:
			rel_path = str(Path(paper_path).relative_to(papers_root_dir))
			target_rel_dir = str(Path(f"{SHARED_PAPER_WAREHOUSE_DIR}/{user_id}/{rel_path}").parent)
			target_dirs.append(target_rel_dir)

		failed_papers = []
		for idx, paper_path in enumerate(paper_paths):
			paper_id = self.insert_single_paper(
				target_rel_dir=target_dirs[idx],
				raw_paper_path=paper_path,
			)
			if paper_id is None:
				failed_papers.append(paper_path)
				continue
			if enable_summarize:
				self.summarize_paper(paper_node_id=paper_id)
			self.persist_papers()
			self.persist_notes()

		if len(failed_papers) < 1:
			return None
		return failed_papers

	async def ainsert_papers(
		self,
		user_id: str,
		papers_root_dir: str,
		paper_paths: List[str],
		enable_summarize: bool
	) -> Optional[List[str]]:
		r"""
		Asynchronously insert papers of a user.

		Args:
			user_id (str): The user id of a laboratory member.
			papers_root_dir (str): The raw root directory of these papers,
				the directory structure will be copied to the shared paper warehouse.
			paper_paths (List[str]): The paths of the papers.
			enable_summarize (bool): Whether to summarize these papers.

		Returns:
			Optional[List[str]]: The paths of failed papers. If no paper fails in recording, return None.
		"""
		target_dirs = []
		for paper_path in paper_paths:
			rel_path = str(Path(paper_path).relative_to(papers_root_dir))
			target_rel_dir = f"{SHARED_PAPER_WAREHOUSE_DIR}/{user_id}/{rel_path}"
			target_dirs.append(target_rel_dir)

		failed_papers = []
		for idx, paper_path in enumerate(paper_paths):
			paper_id = self.insert_single_paper(
				target_rel_dir=target_dirs[idx],
				raw_paper_path=paper_path,
			)
			if paper_id is None:
				failed_papers.append(paper_path)
				continue
			if enable_summarize:
				await self.asummarize_paper(paper_node_id=paper_id)
			self.persist_papers()
			self.persist_notes()

		if len(failed_papers) < 1:
			return None
		return failed_papers

	def persist_papers(self, persist_dir: str = None):
		r""" Save the vector_index to disk. """
		persist_dir = persist_dir or self.persist_dir
		if not self._fs.exists(persist_dir):
			self._fs.makedirs(persist_dir)
		self.vector_index.storage_context.persist(persist_dir=persist_dir)

	def persist_notes(
		self,
		notes_persist_dir: str = None,
	):
		r""" Save the notes_vector_index to disk. """
		notes_persist_dir = notes_persist_dir or self.notes_persist_dir
		if not self._fs.exists(notes_persist_dir):
			self._fs.makedirs(notes_persist_dir)
		self.notes_vector_index.storage_context.persist(persist_dir=notes_persist_dir)

	def insert_note(
		self,
		doi: str,
		page_label: int,
		chunk_info: str,
		user_id: str,
		note: str,
	) -> bool:
		r"""
		Insert a note into the notes vector index.

		Args:
			doi (str): The DOI of the corresponding paper.
			page_label (int): The page label of the note location.
			user_id (str): The user id of a Lab member.
			chunk_info (str): The chunk info corresponding to the note
			note (str): The user's note.

		Returns:
			bool: successful or not.
		"""
		self._account_manager.check_valid_user(user_id=user_id)
		doi_node = self._get_notes_index_node(node_id=doi)
		if doi_node is None:
			return False

		paper_pages_num = doi_node.child_nodes[0].metadata[SHARED_PAPER_TOTAL_PAGES_KEY]
		if page_label > paper_pages_num:
			return False

		chunk_ids = [node.node_id for node in doi_node.child_nodes]
		page_label_filter = MetadataFilter(
			key=SHARED_PAPER_PAGE_LABEL_KEY,
			value=str(page_label),
			operator=FilterOperator.EQ
		)
		retriever = self.notes_vector_index.as_retriever(similarity_top_k=1)
		retriever._node_ids = chunk_ids
		retriever._filters = MetadataFilters(filters=[page_label_filter])

		retrieved_nodes = retriever.retrieve(chunk_info)
		if not retrieved_nodes:
			return False

		target_node_id = retrieved_nodes[0].node_id
		chunk_node = self._get_notes_index_node(node_id=target_node_id)
		note_node = self._new_note_node(
			user_id=user_id,
			note=note,
		)
		if chunk_node.metadata[SHARED_PAPER_CHUNK_LAST_NOTE_KEY] is None:
			chunk_node.metadata[SHARED_PAPER_CHUNK_INIT_NOTE_KEY] = note_node.node_id
			chunk_node.metadata[SHARED_PAPER_CHUNK_LAST_NOTE_KEY] = note_node.node_id
		else:
			last_note_id = chunk_node.metadata[SHARED_PAPER_CHUNK_LAST_NOTE_KEY]
			last_note = self._get_notes_index_node(node_id=last_note_id)
			last_note.relationships[NodeRelationship.NEXT] = RelatedNodeInfo(node_id=note_node.node_id)
			note_node.relationships[NodeRelationship.PREVIOUS] = RelatedNodeInfo(node_id=last_note_id)
			chunk_node.metadata[SHARED_PAPER_CHUNK_LAST_NOTE_KEY] = note_node.node_id
			self._update_note_index_node(node_id=last_note_id, node=last_note)

		self._insert_as_child_nodes(node=chunk_node, child_nodes=[note_node])
		self._update_note_index_node(node_id=chunk_node.node_id, node=chunk_node)
		self._update_note_index_node(node_id=note_node.node_id, node=note_node)
		self.persist_notes()
		return True

	def _get_chunk_notes(
		self,
		chunk_node: BaseNode,
	) -> Optional[ChunkNote]:
		r"""
		Get the notes belonging to the chunk node.

		Args:
			chunk_node (BaseNode): The chunk node.

		Returns:
			Optional[ChunkNote]
		"""
		init_note_id = chunk_node.metadata[SHARED_PAPER_CHUNK_INIT_NOTE_KEY]
		if init_note_id is None:
			return None

		note_node = self._get_notes_index_node(node_id=init_note_id)
		doi = chunk_node.parent_node.node_id
		all_notes = []
		while note_node is not None:
			user_note = UserNote(
				doi=doi,
				note=note_node.text,
				date_str=note_node.metadata[SHARED_NOTE_DATE_KEY],
				time_str=note_node.metadata[SHARED_NOTE_TIME_KEY],
				user_id=note_node.metadata["user_id"],
			)
			all_notes.append(user_note)
			next_note = note_node.next_node
			if next_note:
				note_node = self._get_notes_index_node(node_id=next_note.node_id)
			else:
				note_node = None
		page_label = int(chunk_node.metadata[SHARED_PAPER_PAGE_LABEL_KEY])
		return ChunkNote(
			chunk_content=chunk_node.get_content(metadata_mode=MetadataMode.NONE),
			doi=doi,
			page_label=page_label,
			notes=all_notes,
		)

	def get_all_notes(
		self,
		doi: str,
	) -> Optional[List[ChunkNote]]:
		r"""
		Get all notes of a paper.

		Args:
			doi (str): The DOI of a paper.

		Returns:
			Optional[List[ChunkNote]]: The notes.
		"""
		doi_node = self._get_notes_index_node(node_id=doi)
		if doi_node is None:
			return None
		page_notes = defaultdict(list)
		chunk_ids = [node.node_id for node in doi_node.child_nodes]

		for chunk_id in chunk_ids:
			chunk_node = self._get_notes_index_node(node_id=chunk_id)
			chunk_note = self._get_chunk_notes(chunk_node=chunk_node)
			if chunk_note:
				page_label = int(chunk_node.metadata[SHARED_PAPER_PAGE_LABEL_KEY])
				page_notes[page_label].append(chunk_note)
		pages = [(label, page_notes[label]) for label in page_notes.keys()]
		pages.sort(key=lambda x: x[0], reverse=False)
		all_notes = []
		for page in pages:
			all_notes.extend(page[1])
		return all_notes

	def get_notes(
		self,
		doi: str,
		chunk_info: str,
	) -> Optional[List[UserNote]]:
		r"""
		Check whether there exists any notes corresponding to the given content.

		Args:
			doi (str): The DOI of the paper.
			chunk_info (str): The corresponding paper content.

		Returns:
			Optional[List[UserNote]]: If notes exist, return the notes. Otherwise, return None.
		"""
		doi_node = self._get_notes_index_node(node_id=doi)
		if doi_node is None:
			return None
		chunk_ids = [node.node_id for node in doi_node.child_nodes]
		retriever = self.notes_vector_index.as_retriever(similarity_top_k=1)
		retriever._node_ids = chunk_ids
		retrieved_nodes = retriever.retrieve(chunk_info)
		target_node_id = retrieved_nodes[0].node_id
		chunk_node = self._get_notes_index_node(node_id=target_node_id)

		note_ids = [node.node_id for node in chunk_node.child_nodes]
		if len(note_ids) < 1:
			return None

		notes = []
		for node_id in note_ids:
			note_node = self._get_notes_index_node(node_id=node_id)
			notes.append(
				UserNote(
					user_id=note_node.metadata["user_id"],
					note=note_node.text,
					doi=doi,
				)
			)
		return notes

	def add_user_node(self, user_id: str) -> BaseNode:
		r"""
		Add a user node for a valid user.

		Args:
			user_id (str): The user id of a Lab member.

		Returns:
			The user node
		"""
		user_node = TextNode(
			text=f"Directory for user {user_id}",
			id_=user_id,
			metadata={
				SHARED_PAPER_NODE_TYPE: SharedPaperNodeType.USER,
			}
		)
		root_node = self._get_node(node_id=SHARED_PAPER_ROOT_NODE_NAME)
		self._insert_as_child_nodes(node=root_node, child_nodes=[user_node])
		self._update_node(node_id=root_node.node_id, node=root_node)
		self._update_node(node_id=user_node.node_id, node=user_node)
		return user_node


if __name__ == "__main__":
	from labridge.models.utils import get_models

	llm_model, embedding_model = get_models()

	paper_store = SharedPaperStorage.from_default(llm=llm_model, embed_model=embedding_model)

	root_node = paper_store.notes_vector_index.docstore.get_node(node_id=SHARED_PAPER_ROOT_NODE_NAME)

	acc = AccountManager()
	acc.add_user(user_id="赵懿晨", password="123456")
	acc.add_user(user_id="杨再正", password="123456")


	def add_papers(user_id: str, papers: List[str], user_root: str):
		max_try = 3
		try_idx = 0
		remain_papers = papers

		while remain_papers and try_idx < max_try:
			print(f"Try {try_idx}")
			remain_papers = paper_store.insert_papers(
				user_id=user_id,
				enable_summarize=False,
				paper_paths=remain_papers,
				papers_root_dir=user_root,
			)
			try_idx += 1

		if remain_papers:
			print("Failed papers: \n", remain_papers)


	root_dir = paper_store._root
	zhisan_papers = [
		fr"{root_dir}\documents\papers\杨再正\存算一体\2018 NC Efficient and self-adaptive in-situ learning in multilayer memristor neural networks.pdf",
		fr"{root_dir}\documents\papers\杨再正\存算一体\2019 wangzhongrui In situ training of feed-forward and recurrent convolutional memristor network.pdf",
		fr"{root_dir}\documents\papers\杨再正\神经网络量化\post-training-quantization\Quantization_quantizatoin and_Training_of_Neural_Networks_for_Efficient_Integer-Arithmetic-Only_Inference.pdf",
		fr"{root_dir}\documents\papers\杨再正\神经网络量化\training-aware-quantization\Gong_Differentiable_Soft_Quantization_Bridging_Full-Precision_and_Low-Bit_Neural_Networks_ICCV_2019_paper.pdf",
		fr"{root_dir}\documents\papers\杨再正\神经网络量化\training-aware-quantization\XNOR-Net.pdf",
	]

	zhaoyichen_papers = [
		fr"{root_dir}\documents\papers\赵懿晨\强化学习\PPO.pdf",
		fr"{root_dir}\documents\papers\赵懿晨\深度学习编译\The_Deep_Learning_Compiler_A_Comprehensive_Survey.pdf",
		fr"{root_dir}\documents\papers\赵懿晨\深度学习编译\An_In-depth_Comparison_of_Compilers_for_Deep_Neural_Networks_on_Hardware.pdf",
		fr"{root_dir}\documents\papers\赵懿晨\深度学习编译\CIM\A Compilation Tool for Computation Offloading in ReRAM-based CIM Architectures.pdf",
		fr"{root_dir}\documents\papers\赵懿晨\深度学习编译\CIM\A_Compilation_Framework_for_SRAM_Computing-in-Memory_Systems_With_Optimized_Weight_Mapping_and_Error_Correction.pdf",
		fr"{root_dir}\documents\papers\赵懿晨\深度学习编译\CIM\C4CAM_ACompiler for CAM-based In-memory Accelerators.pdf",
		fr"{root_dir}\documents\papers\赵懿晨\深度学习编译\CIM\CIM-MLC_AMulti-level Compilation Stack for Computing-in-memory accelerators.pdf",
		fr"{root_dir}\documents\papers\赵懿晨\深度学习编译\CIM\CIMAX-Compiler_An_End-to-End_ANN_Compiler_for_Heterogeneous_Computing-in-Memory_Platform.pdf",
	]

	add_papers(user_id="杨再正", papers=zhisan_papers, user_root=fr"{root_dir}\documents\papers\杨再正")
	add_papers(user_id="赵懿晨", papers=zhaoyichen_papers, user_root=fr"{root_dir}\documents\papers\赵懿晨")

	# paper_store.insert_note(
	# 	doi="10.1038/s41467-018-04484-2",
	# 	user_id="zhisan",
	# 	notes={
	# 		"they do not have a significant impact on MNIST classification accuracy": "这里的原因是由于鲁棒性",
	# 		"A further potential benefit of utilizing analog computation in a memristor-based neural network is a substantial improvement in speed-energy efficiency.": "对比一下其它的硬件效率",
	# 	}
	# )
	#
	# for child in root_node.child_nodes:
	# 	print("DOI: ", child.node_id)
	# 	doi_node = paper_store._get_notes_index_node(node_id=child.node_id)
	#
	# 	for chunk in doi_node.child_nodes:
	# 		print("Chunk: ", chunk.node_id)
	# 		chunk_node = paper_store._get_notes_index_node(node_id=chunk.node_id)
	# 		print(chunk_node.metadata)
	#
	# 		if chunk_node.child_nodes is None:
	# 			continue
	#
	# 		for note in chunk_node.child_nodes:
	# 			print("Note: ", note.node_id)
	# 			note_node = paper_store._get_notes_index_node(node_id=note.node_id)
	# 			print(note_node.get_content())
	#
	# notes = paper_store.get_notes(
	# 	doi="10.1038/s41467-018-04484-2",
	# 	chunk_info="they do not have a significant impact on MNIST classification accuracy",
	# )
	#
	# for each_note in notes:
	# 	print(each_note.user_id, each_note.doi, each_note.note)

	# vector_root_node = paper_store.vector_index.docstore.get_node(node_id=SHARED_PAPER_ROOT_NODE_NAME)
	#
	# for child in vector_root_node.child_nodes:
	# 	print(child.node_id)
	# 	child_node = paper_store._get_node(node_id=child.node_id)
	# 	if child_node.child_nodes is None:
	# 		continue
	#
	# 	for dir_path in child_node.child_nodes:
	# 		dir_node = paper_store._get_node(node_id=dir_path.node_id)
	# 		print("node_id: ", dir_node.node_id, "metadata: ", dir_node.metadata)
	#
	# 		for paper in dir_node.child_nodes:
	# 			paper_node = paper_store._get_node(node_id=paper.node_id)
	# 			print("paper node id: ", paper_node.node_id, "metadata: ", paper_node.metadata)
	#
	# 			for doc in paper_node.child_nodes:
	# 				doc_node = paper_store._get_node(node_id=doc.node_id)
	# 				print("doc node id: ", doc_node.node_id, "metadata: ", doc_node.metadata)




