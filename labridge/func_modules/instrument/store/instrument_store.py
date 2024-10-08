import fsspec

from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.settings import Settings
from llama_index.core import load_index_from_storage
from llama_index.core.storage import StorageContext
from llama_index.core.ingestion import run_transformations
from llama_index.core.schema import (
	TextNode,
	NodeRelationship,
	RelatedNodeInfo,
	BaseNode,
	TransformComponent,
)
from llama_index.core.readers import SimpleDirectoryReader

from pathlib import Path
from typing import List, Dict, Any, Union
from labridge.accounts.super_users import InstrumentSuperUserManager


DEFAULT_INSTRUMENT_VECTOR_PERSIST_DIR = "storage/instruments"
DEFAULT_INSTRUMENT_WAREHOUSE_DIR = "documents/instruments"

INSTRUMENT_VECTOR_INDEX_ID = "instrument_vector_index"
INSTRUMENT_ROOT_NODE_NAME = "root_node"

INSTRUMENT_FILE_PATH_KEY = "file_path"
INSTRUMENT_NAME_KEY = "instrument_name"


def instrument_get_file_metadata(file_path: str) -> Dict[str, Any]:
	r"""
	Get the metadata of instrument doc nodes.
	This function will be used in the `SimpleDirectoryReader`.

	Args:
		file_path (str): The file path of a instrument document.

	Returns:
		Dict[str, Any]:
			These metadata will be recorded in each doc node:

			- the path relative to the project root.
			- the instrument id.
	"""
	root = Path(__file__)
	for i in range(5):
		root = root.parent

	rel_path = Path(file_path).relative_to(root)
	instrument_name = Path(file_path).parts[-2]
	metadata = {
		INSTRUMENT_FILE_PATH_KEY: str(rel_path),
		INSTRUMENT_NAME_KEY: instrument_name
	}
	return metadata


class InstrumentStorage(object):
	r"""
	This class is used for the storage of instrument documents.

	Args:
		vector_index (VectorStoreIndex): The vector database that stores the instrument documents.
		persist_dir (str): The save path of the vector_index.
		embed_model (BaseEmbedding): The used embedding model.
	"""
	def __init__(
		self,
		vector_index: VectorStoreIndex = None,
		persist_dir: str = None,
		embed_model: BaseEmbedding = None
	):
		root = Path(__file__)
		for i in range(5):
			root = root.parent
		self.root = root
		self.vector_index = vector_index
		self.vector_index.set_index_id(INSTRUMENT_VECTOR_INDEX_ID)
		self.embed_model = embed_model
		self.persist_dir = persist_dir or self._default_persist_dir()
		self.instrument_ware_house_dir = self._default_warehouse_dir()

	def _default_persist_dir(self) -> str:
		r""" Return the default save directory of the instrument vector index. """
		return str(self.root / DEFAULT_INSTRUMENT_VECTOR_PERSIST_DIR)

	def _default_warehouse_dir(self) -> str:
		r""" Returns the default save directory of the instrument documents. """
		return str(self.root / DEFAULT_INSTRUMENT_WAREHOUSE_DIR)

	@classmethod
	def from_storage(
		cls,
		persist_dir: str,
		embed_model: BaseEmbedding,
	):
		r"""
		Construct from an existing storage.

		Args:
			persist_dir (str): The persis_dir of an existing InstrumentStorage.
			embed_model (BaseEmbedding): The used embedding model.

		Returns:
			InstrumentStorage: The loaded storage.
		"""
		vector_storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
		vector_index = load_index_from_storage(
			storage_context=vector_storage_context,
			index_id=INSTRUMENT_VECTOR_INDEX_ID,
			embed_model=embed_model,
		)
		return cls(
			vector_index=vector_index,
			persist_dir=persist_dir,
		)

	@classmethod
	def from_default(
		cls,
		embed_model: BaseEmbedding = None,
	):
		r"""
		Load the default instrument storage.

		Args:
			embed_model (BaseEmbedding): The used embedding model.

		Returns:
			InstrumentStorage: The loaded storage.
		"""
		root = Path(__file__)
		for i in range(5):
			root = root.parent
		persist_dir = str(root / DEFAULT_INSTRUMENT_VECTOR_PERSIST_DIR)

		embed_model = embed_model or Settings.embed_model
		fs = fsspec.filesystem("file")
		if fs.exists(persist_dir):
			return cls.from_storage(
				persist_dir=persist_dir,
				embed_model=embed_model,
			)
		root_node = TextNode(
			text="root node for the instruments.",
			id_=INSTRUMENT_ROOT_NODE_NAME
		)
		nodes = [root_node]
		vector_index = VectorStoreIndex(
			nodes=nodes,
			embed_model=embed_model,
		)

		return cls(
			vector_index=vector_index,
			persist_dir=persist_dir,
			embed_model=embed_model,
		)

	def _add_instrument_docs_to_warehouse(
		self,
		instrument_id: str,
		instrument_doc_paths: List[str],
	) -> List[str]:
		r"""
		Store the instrument documents in the instrument warehouse.

		Args:
			instrument_id (str): The instrument name.
			instrument_doc_paths (InstrumentStorage): The file paths of the instrument's documents.

		Returns:
			List[str]: The file paths of the stored instrument documents
		"""
		fs = fsspec.filesystem("file")
		warehouse_dir = self.root / DEFAULT_INSTRUMENT_WAREHOUSE_DIR
		instrument_dir = warehouse_dir / instrument_id

		if not fs.exists(str(instrument_dir)):
			fs.makedirs(str(instrument_dir))

		for doc_path in instrument_doc_paths:
			if not fs.exists(doc_path):
				raise ValueError(f"Error: {doc_path} do not exist!")

		store_paths = []
		for doc_path in instrument_doc_paths:
			fs.cp(doc_path, str(instrument_dir))
			doc_name = Path(doc_path).name
			store_paths.append(
				str(instrument_dir / doc_name)
			)
		return store_paths

	def _default_vector_transformations(self) -> List[TransformComponent]:
		r""" Default transformations of the vector index. """
		return [SentenceSplitter(chunk_size=1024, chunk_overlap=256, include_metadata=True), ]

	def get_nodes(self, node_ids: List[str]) -> List[BaseNode]:
		r"""
		Get the nodes according to node_ids.

		Args:
			node_ids (List[str]): The node ids.

		Returns:
			List[BaseNode]: The corresponding nodes in the vector index.

		Raises:
			ValueError: If any node_id does not exist in the vector index.
		"""
		return self.vector_index.docstore.get_nodes(node_ids=node_ids)

	def _get_node(self, node_id: str) -> BaseNode:
		r""" get node from the vector index """
		return self.vector_index.docstore.get_node(node_id)

	def _update_node(
		self,
		node_id: str,
		node: BaseNode,
	):
		r""" update node in vector index """
		self.vector_index.delete_nodes([node_id])
		self.vector_index.insert_nodes([node])

	def get_all_instruments(self) -> List[str]:
		r"""
		Get all instrument ids.

		Returns:
			List[str]: All instrument ids.
		"""
		root_node = self._get_node(node_id=INSTRUMENT_ROOT_NODE_NAME)
		instrument_list = root_node.child_nodes or []
		instrument_ids = [ins.node_id for ins in instrument_list]
		return instrument_ids

	def add_instrument(
		self,
		instrument_id: str,
		instrument_description: str,
		instrument_doc_paths: List[str],
		super_user_ids: List[str],
	):
		r"""
		Add a new instrument to storage.

		1. Add a text node containing the instrument id and description, and add it to the root_node's children.
		2. Add the instrument document nodes as the children of the instrument node.

		Args:
			instrument_id (str): The instrument name.
			instrument_description (str): The instrument description.
			instrument_doc_paths (List[str]): The file paths of the instrument's documents.
			super_user_ids (List[str]): The supe-users of the instrument.
		"""
		# Add to instrument manager
		manager = InstrumentSuperUserManager()
		manager.add_instrument(
			instrument_id=instrument_id,
			super_users=super_user_ids,
		)
		# add instrument node to root node.
		root_node = self._get_node(node_id=INSTRUMENT_ROOT_NODE_NAME)
		print("root_node childs: ", root_node.child_nodes)
		instrument_list = root_node.child_nodes or []

		instrument_node = TextNode(
			text=instrument_description,
			id_=instrument_id,
		)
		instrument_list.append(
			RelatedNodeInfo(node_id=instrument_node.node_id)
		)
		root_node.relationships[NodeRelationship.CHILD] = instrument_list
		self._update_node(node_id=INSTRUMENT_ROOT_NODE_NAME, node=root_node)

		self.vector_index.insert_nodes(nodes=[instrument_node])

		self.add_instrument_doc(
			instrument_id=instrument_id,
			doc_path=instrument_doc_paths,
		)

	def add_instrument_doc(
		self,
		instrument_id: str,
		doc_path: Union[str, List[str]]
	):
		r"""
		Add documents to an instrument's docs.

		Args:
			instrument_id (str): The instrument name.
			doc_path (Union[str, List[str]]): New documents of the instrument.
		"""
		instrument_node = self._get_node(node_id=instrument_id)
		if not isinstance(doc_path, list):
			doc_path = [doc_path]

		if len(doc_path) < 1:
			return

		path_list = self._add_instrument_docs_to_warehouse(
			instrument_id=instrument_id,
			instrument_doc_paths=doc_path,
		)

		# read the docs.
		reader = SimpleDirectoryReader(
			input_files=path_list,
			file_metadata=instrument_get_file_metadata,
			filename_as_id=True,
			recursive=True,
		)
		documents = reader.load_data()

		for doc in documents:
			self.vector_index.docstore.set_document_hash(doc.get_doc_id(), doc.hash)

		# chunk to nodes.
		doc_nodes = run_transformations(nodes=documents, transformations=self._default_vector_transformations(), )

		child_nodes = instrument_node.child_nodes or []
		for doc_node in doc_nodes:
			child_nodes.append(RelatedNodeInfo(node_id=doc_node.node_id))
			doc_node.relationships[NodeRelationship.PARENT] = RelatedNodeInfo(node_id=instrument_id)

		instrument_node.relationships[NodeRelationship.CHILD] = child_nodes

		self._update_node(node_id=instrument_id, node=instrument_node)
		self.vector_index.insert_nodes(nodes=doc_nodes)

	def delete_instrument_doc(
		self,
		instrument_id: str,
		doc_rel_path: Union[str, List[str]],
	):
		r"""
		Delete specific docs from the instrument storage and warehouse according to the relative path of the document.

		Args:
			instrument_id (str): The instrument name.
			doc_rel_path (str): The document path relative to root.
		"""
		instrument_node = self._get_node(node_id=instrument_id)
		child_node_list = instrument_node.child_nodes

		if not isinstance(doc_rel_path, list):
			doc_rel_path = [doc_rel_path]

		delete_node_ids = []
		for child_node in child_node_list:
			node_id = child_node.node_id
			doc_node = self._get_node(node_id=node_id)
			if doc_node.metadata[INSTRUMENT_FILE_PATH_KEY] in doc_rel_path:
				delete_node_ids.append(node_id)
				child_node_list.remove(child_node)

		instrument_node.relationships[NodeRelationship.CHILD] = child_node_list
		self._update_node(node_id=instrument_id, node=instrument_node)
		self.vector_index.delete_nodes(node_ids=delete_node_ids)

		fs = fsspec.filesystem("file")
		for rel_path in doc_rel_path:
			abs_path = str(self.root / rel_path)
			fs.rm(abs_path)

	def update_instrument_doc(
		self,
		instrument_id: str,
		instrument_doc_name: str,
		new_doc_path: str,
	):
		r"""
		Update an instrument document with a new document.

		Args:
			instrument_id (str): The instrument name.
			instrument_doc_name (str): The old instrument document name.
			new_doc_path (str): The path of the new document.
		"""
		old_doc_path = Path(DEFAULT_INSTRUMENT_WAREHOUSE_DIR) / instrument_doc_name
		old_doc_path = str(old_doc_path)

		self.delete_instrument_doc(
			instrument_id=instrument_id,
			doc_rel_path=old_doc_path,
		)
		self.add_instrument_doc(
			instrument_id=instrument_id,
			doc_path=new_doc_path,
		)

	def persist(self, persist_dir: str = None):
		r""" Save the storage. """
		persist_dir = persist_dir or self.persist_dir
		fs = fsspec.filesystem("file")
		if not fs.exists(persist_dir):
			fs.makedirs(persist_dir)
		self.vector_index.storage_context.persist(persist_dir=persist_dir)


if __name__ == "__main__":
	fs = fsspec.filesystem("file")

	# root = Path(__file__)
	# for i in range(5):
	# 	root = root.parent
	# raw_path = root / "storage/test.txt"
	# new_path = root / "test.txt"
	#
	# # fs.cp(str(raw_path), str(root))
	# fs.rm(str(new_path))

	from labridge.models.utils import get_models

	llm, embedding_model = get_models()
	instruments = InstrumentStorage.from_default(embed_model=embedding_model)

	instruments.add_instrument(
		instrument_id="DSOX3012G示波器",
		instrument_description=(
			"DSOX3012G 100 MHz 示波器提供了 2 个模拟通道、4 Mpts 存储器和 1,000,000 波形/秒的捕获率，"
			"以及 8.5 英寸电容触摸屏和区域触摸触发功能，同时标配嵌入式软件，其中可提供波形和测量直方图。\n"
			"特点包括：\n"
			"100 MHz 带宽和 2 个模拟通道。"
			"8.5 英寸电容触摸屏让您可以轻松查看和分析信号。"
			"独有的区域触摸触发技术让您只需几秒钟便可轻松隔离信号"
			"高达 1,000,000 波形/秒的捕获率为您呈现更详细的信号细节。"
			"高达 4 Mpts 的存储器可以捕获更多的数据。"
			"支持全面升级，可以扩展测量功能：随时增加带宽、数字通道数量和先进的应用软件。"
		),
		instrument_doc_paths=["E:\yzz\Labridge\documents\instrument_raw_docs\InfiniiVision 3000G X-Series Oscilloscopes.pdf"],
		super_user_ids=["杨再正"],
	)

	instruments.add_instrument(
		instrument_id="手持测温热成像仪TP41",
		instrument_description=(
			"可以通过红外热成像获取电路板各区域的温度分布情况，进一步判断是否存在发热情况。\n"
			"产品简介：\n"
			"TP4系列是海康微影口袋型手持测温产品，搭载192*144红外探测器。800万像素的可见光相机模块，支持热成像和可见光视频拍照和录制功能，"
			"再搭配上强大专业的手机APP和电脑软件，为每一位工程师提供更专业的红外热成像服务。"
			"功能特性：\n"
			"支持1.x~4.x连续数字变倍。"
			"支持视频拍照和录制。"
			"支持手机APP和电脑软件实时查看及二次分析。"
			"测温范围-20℃-400℃。"
			"支持扩展微距镜头。"
		),
		instrument_doc_paths=["E:\yzz\Labridge\documents\instrument_raw_docs\hkws.pdf"],
		super_user_ids=["赵懿晨"],
	)
	instruments.persist()

	ids = instruments.get_all_instruments()

	ins_nodes = instruments.get_nodes(ids)

	for node in ins_nodes:
		print(node.text)
		print(node.child_nodes)
	print(ids)

