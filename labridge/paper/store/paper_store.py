import os
import random

from typing import Optional, Tuple, List, Union, cast, Dict, Any
from pathlib import Path

from llama_index.core.indices.document_summary import DocumentSummaryIndex
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.readers.file.pymu_pdf import PyMuPDFReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.service_context import ServiceContext
from llama_index.core.storage import StorageContext
from llama_index.core import load_index_from_storage
from llama_index.core.indices.utils import embed_nodes
from llama_index.core.base.response.schema import Response
from llama_index.core.utils import print_text
from llama_index.core.llms import LLM
from llama_index.core.schema import (
	Document,
	TransformComponent,
	NodeRelationship,
	RelatedNodeInfo,
	TextNode,
	NodeWithScore,
)
from llama_index.core.settings import (
    Settings,
    embed_model_from_settings_or_context,
    llm_from_settings_or_context,
)
from llama_index.core.response_synthesizers import (
    BaseSynthesizer,
    ResponseMode,
    get_response_synthesizer,
)
from llama_index.core.indices.utils import (
    default_format_node_batch_fn,
    default_parse_choice_select_answer_fn,
)

from ..download.arxiv import ArxivCategory
from ..prompt.store.dir_summary import (
	DIR_SUMMARIZE_QUERY,
	PAPER_KEYWORDS_EXTRACT_QUERY,
	DIR_CHOICE_SELECT_PROMPT,
	CATEGORY_CHOICE_SELECT_PROMPT,
)
from ..parse.extractors.metadata_extract import (
	PAPER_POSSESSOR,
	PAPER_LEVEL_KEYWORDS,
)
from ..parse.parsers.base import (
	MAINTEXT,
	METHODS,
	CONTENT_TYPE_NAME,
)
from ..prompt.store.paper_summary import (
	PAPER_SUMMARIZE_QUERY,
	METHODS_SUMMARIZE_QUERY,
)


PAPER_VECTOR_INDEX_ID = "vector_index"
PAPER_SUMMARY_INDEX_ID = "paper_summary_index"
DIR_SUMMARY_INDEX_ID = "directory_summary_index"

DIR_CATEGORY_NAME = "categories"

SummarizeQueries = {
	MAINTEXT: PAPER_SUMMARIZE_QUERY,
	METHODS: METHODS_SUMMARIZE_QUERY,
}

DEFAULT_PAPER_WAREHOUSE_DIR = "docs/papers"
DEFAULT_PAPER_VECTOR_PERSIST_DIR = "storage/papers/vector_index"
DEFAULT_PAPER_SUMMARY_PERSIST_DIR = "storage/papers/paper_summary_index"
DEFAULT_DIRECTORY_SUMMARY_PERSIST_DIR = "storage/papers/directory_summary_index"


class PaperStorage:
	r"""
	Store the papers in vector index and summary index.
	The vector index stores the text chunks of the main text (and methods) and their embeddings.
	The summary index stores the summaries of the papers.
	Note that they can not share the storage context.

	Args:
		docs (List[Document]): the Documents to be stored.
		extra_docs (List[Document]): extra Documents (like References),
			they are stored in the docstore of the index.
		vector_index (VectorStoreIndex): existing vector index.
		vector_persist_dir (Union[str, os.PathLike]): the store directory of the vector index.
		vector_transformations (List[TransformComponent]): the transformations used in the construction of the vector index.
		paper_summary_index (DocumentSummaryIndex): existing summary index.
		paper_summary_persist_dir (Union[str, os.PathLike]): the store directory of the summary index.
		paper_summary_query (str): the query used in summarizing the papers.
		summary_transformations (List[TransformComponent]): the transformations used in the construction of the summary index.
		summary_synthesizer (BaseSynthesizer): the synthesizer used in summarizing the papers.
		vector_storage_context (StorageContext): the storage context of the vector index.
		paper_summary_storage_context (StorageContext): the storage context of the summary index.
		service_context (ServiceContext): the service context.
	"""
	def __init__(self,
				 docs: Optional[List[Document]] = None,
				 extra_docs: Optional[List[Document]] = None,
				 vector_index: Optional[VectorStoreIndex] = None,
				 vector_persist_dir: Union[str, os.PathLike] = None,
				 vector_transformations: List[TransformComponent] = None,
				 paper_summary_index: Optional[DocumentSummaryIndex] = None,
				 paper_summary_persist_dir: Union[str, os.PathLike] = None,
				 paper_summary_query: str = PAPER_SUMMARIZE_QUERY,
				 summary_transformations: List[TransformComponent] = None,
				 summary_synthesizer: Optional[BaseSynthesizer] = None,
				 vector_storage_context: Optional[StorageContext] = None,
				 paper_summary_storage_context: Optional[StorageContext] = None,
				 service_context: Optional[ServiceContext] = None,):
		root = Path(__file__)
		for i in range(4):
			root = root.parent
		self.root = root
		self.llm = llm_from_settings_or_context(Settings, service_context)
		self.embed_model = embed_model_from_settings_or_context(Settings, service_context)
		self.service_context = service_context
		self.vector_persist_dir = vector_persist_dir or self._default_vector_persist_dir()
		self.paper_summary_persist_dir = paper_summary_persist_dir or self._default_paper_summary_persist_dir()
		self.vector_transformations = vector_transformations or self._default_vector_transformations()
		self.summary_transformations = summary_transformations or self._default_summary_transformations()
		self.summary_synthesizer = summary_synthesizer
		self.paper_summary_query = paper_summary_query
		if summary_synthesizer is None:
			self.summary_synthesizer = get_response_synthesizer(llm=self.llm, response_mode=ResponseMode.TREE_SUMMARIZE)

		if (vector_index is None or paper_summary_index is None) and (docs is None or extra_docs is None):
			raise ValueError("Please provide (docs, extra_docs) or existed (vector_index, summary_index).")
		if None not in (vector_index, paper_summary_index):
			assert vector_index.storage_context != paper_summary_index.storage_context
			self.vector_index, self.paper_summary_index = vector_index, paper_summary_index
			self.vector_storage_context = vector_index.storage_context
			self.paper_summary_storage_context = paper_summary_index.storage_context
		else:
			self.vector_storage_context = vector_storage_context or StorageContext.from_defaults()
			self.paper_summary_storage_context = paper_summary_storage_context or StorageContext.from_defaults()
			self.build_index_from_docs(docs=docs, extra_docs=extra_docs)

	def _default_vector_persist_dir(self) -> str:
		return str(self.root / DEFAULT_PAPER_VECTOR_PERSIST_DIR)

	def _default_paper_summary_persist_dir(self) -> str:
		return str(self.root / DEFAULT_PAPER_SUMMARY_PERSIST_DIR)

	def _default_vector_transformations(self) -> List[TransformComponent]:
		return [SentenceSplitter(chunk_size=1024, chunk_overlap=256, include_metadata=True), ]

	def _default_summary_transformations(self) -> List[TransformComponent]:
		return [SentenceSplitter(chunk_size=1024, chunk_overlap=256, include_metadata=True), ]

	def build_vector_index_from_docs(self, docs: List[Document]) -> VectorStoreIndex:
		if not self._are_valid_docs(docs):
			raise ValueError(f"Doc not in paper warehouse.")
		vector_index = VectorStoreIndex.from_documents(documents=docs,
													   storage_context=self.vector_storage_context,
													   show_progress=True,
													   transformations=self.vector_transformations,
													   service_context=self.service_context)
		vector_index.set_index_id(PAPER_VECTOR_INDEX_ID)
		return vector_index

	def build_paper_summary_index_from_docs(self, docs: List[Document]) -> DocumentSummaryIndex:
		if not self._are_valid_docs(docs):
			raise ValueError(f"Doc not in paper warehouse.")
		paper_summary_index = DocumentSummaryIndex.from_documents(
			documents=docs,
			storage_context=self.paper_summary_storage_context,
			show_progress=True,
			transformations=self.summary_transformations,
			summary_query = self.paper_summary_query,
			service_context=self.service_context,
		)
		paper_summary_index.set_index_id(PAPER_SUMMARY_INDEX_ID)
		return paper_summary_index

	def build_index_from_docs(self,
							  docs: List[Document],
							  extra_docs: List[Document],):
		if not self._are_valid_docs(docs + extra_docs):
			raise ValueError(f"Doc not in paper warehouse.")

		self.vector_index = self.build_vector_index_from_docs(docs=docs[:1])
		self.paper_summary_index = self.build_paper_summary_index_from_docs(docs=docs[:1])
		self.persist()
		self.insert(paper_docs=docs[1:], extra_docs=extra_docs)
		# vector_index = self.build_vector_index_from_docs(docs)
		# paper_summary_index = self.build_paper_summary_index_from_docs(docs)
		# vector_index.docstore.add_documents(extra_docs)
		# paper_summary_index.docstore.add_documents(extra_docs)
		# return vector_index, paper_summary_index

	@classmethod
	def from_storage(cls,
					 vector_persist_dir: str,
					 paper_summary_persist_dir: str,
					 vector_transformations: List[TransformComponent] = None,
					 paper_summary_query: str = PAPER_SUMMARIZE_QUERY,
					 summary_transformations: List[TransformComponent] = None,
					 summary_synthesizer: Optional[BaseSynthesizer] = None,
					 service_context: Optional[ServiceContext] = None,):
		root = Path(__file__)
		for i in range(4):
			root = root.parent

		vector_persist_dir = vector_persist_dir or str(root / DEFAULT_PAPER_VECTOR_PERSIST_DIR)
		paper_summary_persist_dir = paper_summary_persist_dir or str(root / DEFAULT_PAPER_SUMMARY_PERSIST_DIR)
		vector_storage_context = StorageContext.from_defaults(persist_dir=vector_persist_dir)
		paper_summary_storage_context = StorageContext.from_defaults(persist_dir=paper_summary_persist_dir)

		vector_index = load_index_from_storage(
			storage_context=vector_storage_context,
			index_id=PAPER_VECTOR_INDEX_ID,
			service_context=service_context,
		)
		paper_summary_index = load_index_from_storage(
			storage_context=paper_summary_storage_context,
			index_id=PAPER_SUMMARY_INDEX_ID,
			service_context=service_context,
		)

		return cls(
			vector_index=vector_index,
			paper_summary_index=paper_summary_index,
			vector_transformations=vector_transformations,
			vector_persist_dir=vector_persist_dir,
			paper_summary_persist_dir=paper_summary_persist_dir,
			paper_summary_query=paper_summary_query,
			summary_transformations=summary_transformations,
			summary_synthesizer=summary_synthesizer,
			service_context=service_context,
		)

	def _is_valid_doc(self, doc: Document) -> bool:
		r""" Judge whether the paper doc is from the paper warehouse. """
		doc_id = doc.doc_id
		if CONTENT_TYPE_NAME not in doc.metadata.keys():
			return False
		doc_type = doc.metadata[CONTENT_TYPE_NAME]
		rel_path = doc_id.split(f'_{doc_type}')[0]
		doc_path = self.root / rel_path
		return doc_path.exists()

	def _are_valid_docs(self, docs: List[Document]) -> bool:
		for doc in docs:
			if not self._is_valid_doc(doc):
				print(f"Invalid doc. Doc {doc.doc_id} is not in paper warehouse.")
				return False
		return True

	def insert(self, paper_docs: List[Document], extra_docs: List[Document]):
		r"""
		Add new papers to index.
		Assert all new papers are already categorized (that is: they are from the organized paper warehouse.)

		Encourage you to build a storage with one paper first, then use `insert` methods to add other papers,
		because we can control the summarize query depending on each doc's type.

		Args:
			paper_docs (List[Document]): these docs will be summarized; chunked and vectorized.
			extra_docs (List[Document]): these docs are stored in docstore.
		"""
		if not self._are_valid_docs(paper_docs + extra_docs):
			raise ValueError(f"Doc not in paper warehouse.")

		for doc in paper_docs:
			doc_type = doc.doc_id.split('_')[-1]
			if doc_type not in SummarizeQueries.keys():
				raise ValueError(f'Invalid paper doc type: {doc_type}. Acceptable: {list(SummarizeQueries.keys())}.')
			sum_query = SummarizeQueries[doc_type]
			self.paper_summary_index._summary_query = sum_query

			if doc.doc_id not in self.paper_summary_index.docstore.get_all_ref_doc_info().keys():
				self.paper_summary_index.insert(document=doc)
			if doc.doc_id not in self.vector_index.docstore.get_all_ref_doc_info().keys():
				self.vector_index.insert(document=doc)

		self.vector_index.docstore.add_documents(extra_docs)
		self.paper_summary_index.docstore.add_documents(extra_docs)
		self.persist()

	def persist(self,
				vector_persist_dir: Union[str, os.PathLike] = None,
				paper_summary_persist_dir: Union[str, os.PathLike] = None):
		if vector_persist_dir is None:
			vector_persist_dir = self.vector_persist_dir
		if paper_summary_persist_dir is None:
			paper_summary_persist_dir = self.paper_summary_persist_dir
		self.vector_storage_context.persist(vector_persist_dir)
		self.paper_summary_storage_context.persist(paper_summary_persist_dir)


class PaperDirectorySummaryStore:
	r"""
	This class is used to store the summary of each paper directory.
	It is useful for storing new papers in proper directories, recommending papers to lab members, etc.

	Initially, the directory summary store is automatically constructed using LLM to summarize each directory.
	However, it is not accurate enough, it should be updated according to the relevant research fields information
	provided by Lab members.

	Before storing directory summaries, make sure that all target papers have been added to the paper warehouse and
	stored in the `PaperStorage`.

	Each directory summary node is stored in the docstore, two items are recorded:

	1. the possessor of this directory.
	2. the summary (relevant research fields) of this directory.

	These two items are stored as metadata of th summary node.

	Args:
		llm (LLM): the used llm.
		embed_model (BaseEmbedding): the used embed model.
		paper_root (str): the directory root of the paper warehouse.
		paper_summary_persist_dir (str): the directory storing the paper summary index.
		directory_summary_persist_dir (str): the directory storing the directory summary index.
		service_context (ServiceContext): service_context
		dir_choice_batch_size (int):
	"""
	def __init__(
		self,
		llm: Optional[LLM] = None,
		embed_model: Optional[BaseEmbedding] = None,
		paper_root: Union[os.PathLike, str] = None,
		paper_summary_persist_dir: Union[str, os.PathLike] = None,
		directory_summary_persist_dir: Union[str, os.PathLike] = None,
		service_context: Optional[ServiceContext] = None,
		dir_choice_batch_size: int = 5,
	):
		root = Path(__file__)
		for i in range(4):
			root = root.parent
		self.root = root

		self.llm = llm or llm_from_settings_or_context(Settings, service_context)
		self.embed_model = embed_model or embed_model_from_settings_or_context(Settings, service_context)
		self.service_context = service_context
		self.paper_root = self._path_format(
			path=paper_root,
			default=root / DEFAULT_PAPER_WAREHOUSE_DIR,
		)
		self.paper_summary_persist_dir = self._path_format(
			path=paper_summary_persist_dir,
			default=root / DEFAULT_PAPER_SUMMARY_PERSIST_DIR,
		)
		self.directory_summary_persist_dir = self._path_format(
			path=directory_summary_persist_dir,
			default=root / DEFAULT_DIRECTORY_SUMMARY_PERSIST_DIR,
		)
		if not Path(self.directory_summary_persist_dir).exists():
			self._auto_construct()
		directory_storage_context = StorageContext.from_defaults(persist_dir=self.directory_summary_persist_dir)
		self.directory_summary_index = load_index_from_storage(
			storage_context=directory_storage_context,
			index_id=DIR_SUMMARY_INDEX_ID,
			service_context=self.service_context,
		)
		self.dir_choice_batch_size = dir_choice_batch_size


	def _path_format(self, path: Union[os.PathLike, str], default: Path) -> str:
		if path is None:
			return str(default)
		return path

	def _auto_summarize_dir(self, directory: str, verbose: bool = False):
		r"""
		Automatically summarize each directory under the given directory.
		The given directory must be under the paper root.
		"""
		if directory != self.paper_root and Path(self.paper_root) not in Path(directory).parents:
			raise ValueError("Invalid directory. The input directory should be under the paper warehouse.")

		paper_summary_storage_context = StorageContext.from_defaults(persist_dir=self.paper_summary_persist_dir)
		paper_summary_index = load_index_from_storage(
			storage_context=paper_summary_storage_context,
			index_id=PAPER_SUMMARY_INDEX_ID,
			service_context=self.service_context,
		)
		doc_id_to_summary_id = paper_summary_index._index_struct.doc_id_to_summary_id

		if not Path(self.directory_summary_persist_dir).exists():
			rel_paper_root = Path(self.paper_root).relative_to(self.root)
			root_node = TextNode(text="", id_=str(rel_paper_root), )
			root_node.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(node_id="Paper warehouse", )
			dir_summary_index = DocumentSummaryIndex(
				nodes=[root_node, ],
				llm=self.llm,
				embed_model=self.embed_model,
				service_context=self.service_context,
				response_synthesizer=get_response_synthesizer(
					llm=self.llm,
					response_mode=ResponseMode.COMPACT_ACCUMULATE
				),
			)
		else:
			directory_storage_context = StorageContext.from_defaults(persist_dir=self.directory_summary_persist_dir)
			dir_summary_index = load_index_from_storage(
				storage_context=directory_storage_context,
				index_id=DIR_SUMMARY_INDEX_ID,
				service_context=self.service_context,
			)
		dir_id_to_summary_id = dir_summary_index._index_struct.doc_id_to_summary_id

		def dfs(current_dir: Path):
			if not current_dir.is_dir():
				return

			for child in current_dir.iterdir():
				dfs(child)

			nodes = []
			current_dir_id = str(current_dir.relative_to(self.root))
			if current_dir_id == DEFAULT_PAPER_WAREHOUSE_DIR:
				return

			possessor = current_dir_id.split('/')[2]
			print_text(f">>> Processing: {current_dir}", color="blue", end="\n")
			for child in current_dir.iterdir():
				if not child.is_dir() and child.suffix == ".pdf":
					rel_paper = str(child.relative_to(self.root))
					child_main_text = rel_paper + f"_{MAINTEXT}"
					child_methods = rel_paper + f"_{METHODS}"
					for doc_id in (child_main_text, child_methods):
						if doc_id not in doc_id_to_summary_id.keys() and verbose:
							print(f"{doc_id} not stored into the PaperStorage yet, "
								  f"please insert it into the PaperStorage first.")
						if doc_id in doc_id_to_summary_id.keys():
							summary_id = doc_id_to_summary_id[doc_id]
							paper_summary_node = paper_summary_index.docstore.get_node(summary_id)
							# Get the paper keywords
							if PAPER_LEVEL_KEYWORDS in paper_summary_node.metadata.keys():
								paper_keywords = paper_summary_node.metadata[PAPER_LEVEL_KEYWORDS]
							else:
								# extract keywords.
								paper_keywords = dir_summary_index._response_synthesizer.synthesize(
									query=PAPER_KEYWORDS_EXTRACT_QUERY,
									nodes=[NodeWithScore(node=paper_summary_node)]
								)

							# filter metadata (possessor & paper keywords)
							paper_summary_node.metadata = {
								PAPER_POSSESSOR: possessor,
								PAPER_LEVEL_KEYWORDS: paper_keywords,
							}
							paper_summary_node.set_content("")
							paper_summary_node.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(
								node_id=current_dir_id,
							)
							nodes.append(paper_summary_node)
				elif child.is_dir():
					child_dir_id = str(child.relative_to(self.root))
					if child_dir_id in dir_id_to_summary_id.keys():
						child_summary_id = dir_id_to_summary_id[child_dir_id]
						dir_summary_node = dir_summary_index.docstore.get_node(child_summary_id)
						dir_summary_node.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(
							node_id=current_dir_id,
						)
						nodes.append(dir_summary_node)

			# Summarize current directory based on its children
			nodes_with_scores = [NodeWithScore(node=n) for n in nodes]

			if len(nodes_with_scores) > 0:
				summary_response = dir_summary_index._response_synthesizer.synthesize(
					query=DIR_SUMMARIZE_QUERY,
					nodes=nodes_with_scores,
				)

				summary_response = cast(Response, summary_response)
				dir_summary_node = TextNode(
					text="",
					relationships={NodeRelationship.SOURCE: RelatedNodeInfo(node_id=current_dir_id)},
					metadata={
						PAPER_POSSESSOR: possessor,
						PAPER_LEVEL_KEYWORDS: summary_response.response,
					},
				)

				dir_summary_index.docstore.add_documents([dir_summary_node])
				dir_summary_index._index_struct.doc_id_to_summary_id[current_dir_id] = dir_summary_node.node_id

				id_to_embed_map = embed_nodes([dir_summary_node,], self.embed_model)
				node_with_embedding = dir_summary_node.copy()
				node_with_embedding.embedding = id_to_embed_map[dir_summary_node.node_id]
				dir_summary_index._vector_store.add([node_with_embedding, ])
				dir_summary_index._storage_context.index_store.add_index_struct(dir_summary_index._index_struct)

		dfs(Path(directory))
		if dir_summary_index.index_id != DIR_SUMMARY_INDEX_ID:
			dir_summary_index.set_index_id(DIR_SUMMARY_INDEX_ID)
		dir_summary_index.storage_context.persist(persist_dir=str(self.directory_summary_persist_dir))


	def _auto_construct(self):
		r"""
		Automatically construct the directory summary index based on the paper warehouse.

		DFS the directory tree, directory root: `self.paper_root`.
		The summary (relevant research fields) of each directory is synthesized from its child directories.

		Each summary node of a directory: ref_doc_id: the directory path relative to the root.
		"""
		self._auto_summarize_dir(self.paper_root)

	def get_dir_nodes(self):
		r""" get the valid directory summary nodes """
		dir_id_to_summary_id = self.directory_summary_index._index_struct.doc_id_to_summary_id
		dir_summary_nodes = []
		for dir_id in dir_id_to_summary_id.keys():
			dir_path = self.root / dir_id
			if dir_path.exists():
				summary_id = dir_id_to_summary_id[dir_id]
				summary_node = self.directory_summary_index.docstore.get_node(summary_id)
				dir_summary_nodes.append(summary_node)
		return dir_summary_nodes

	def match_directory_for_new_paper(
		self,
		pdf_path: str,
		possessor: str,
		verbose: bool=False,
	) -> Union[str, None]:
		r"""
		select the most relevant (and deepest) directory for the new paper.

		Args:
			pdf_path (str): the path of the new paper.
			possessor (str): the possessor of this new paper.
			verbose (bool): whether to show progress.

		Returns:
			Union[str, None]:
				The matched directory for the new paper. If no proper directory found, return None.
		"""
		pdf_path = Path(pdf_path)
		if pdf_path.suffix != ".pdf":
			raise ValueError("Only papers with PDF format are supported now.")
		possessor_dir = Path(self.paper_root) / possessor
		if not possessor_dir.exists():
			raise ValueError(f"The member {possessor} do not exist. Please sign up as a member first.")

		pdf_docs = PyMuPDFReader().load_data(file_path=pdf_path)
		# typically, the first page includes conclusive information of a paper.
		first_page = pdf_docs[0].text
		dir_summary_nodes = self.get_dir_nodes()

		selected_nodes = []
		selected_relevances = []

		for idx in range(0, len(dir_summary_nodes), self.dir_choice_batch_size):
			summary_nodes = dir_summary_nodes[idx: idx + self.dir_choice_batch_size]
			dir_context_str = default_format_node_batch_fn(summary_nodes=summary_nodes)

			raw_response = self.llm.predict(
				DIR_CHOICE_SELECT_PROMPT,
				dir_context_str=dir_context_str,
				paper_str=first_page,
			)
			raw_choices, relevances = default_parse_choice_select_answer_fn(raw_response, len(summary_nodes))
			choice_idxs = [choice - 1 for choice in raw_choices]
			choice_summary_nodes = [summary_nodes[ci] for ci in choice_idxs]
			selected_nodes.extend(choice_summary_nodes)
			selected_relevances.extend(relevances)

		if len(selected_nodes) == 0:
			return None

		zipped_list = list(zip(selected_nodes, selected_relevances))
		sorted_list = sorted(zipped_list, key=lambda x: x[1], reverse=True)
		# choose the most relevant and the deepest directory.
		best_dir = sorted_list[0][0].ref_doc_id

		if verbose:
			for node, relevance in sorted_list:
				print_text(f">>> dir: {node.ref_doc_id}, relevance: {relevance}", color="blue", end="\n")
		def sub_dir_nodes(paper_dir: str):
			sub_nodes_with_score = []
			for node, score in sorted_list:
				if Path(paper_dir) in Path(node.ref_doc_id).parents:
					sub_nodes_with_score.append((node, score))
			return sub_nodes_with_score

		sub_list = sub_dir_nodes(best_dir)
		while len(sub_list) > 0:
			sub_list = sorted(sub_list, key=lambda x: x[1], reverse=True)
			best_dir = sub_list[0][0].ref_doc_id
			sub_list = sub_dir_nodes(best_dir)
		return best_dir

	def update(self, dir_description_dict: Dict[str, str]):
		r"""
		Update the relevant research fields of each directory.
		Typically used for manually set each directory's relevant research fields.

		Args:
			dir_description_dict (Dict[str, str]): the descriptions of the paper directories
				- key: the directory path relative to root;
				- value: the relevant research fields of the directory.
		"""
		for dir_id in dir_description_dict.keys():
			self._set_dir_metadata(
				dir_id=dir_id,
				key=PAPER_LEVEL_KEYWORDS,
				val=dir_description_dict[dir_id],
			)

	def _set_dir_metadata(self, dir_id: str, key: str, val: Any):
		dir_id_to_summary_id = self.directory_summary_index._index_struct.doc_id_to_summary_id
		node_collection = self.directory_summary_index.docstore._node_collection

		if dir_id in dir_id_to_summary_id.keys():
			summary_id = dir_id_to_summary_id[dir_id]
			summary_store = self.directory_summary_index.docstore._kvstore._data[node_collection][summary_id]
			summary_store["__data__"]["metadata"][key] = val

		self.directory_summary_index.storage_context.persist(persist_dir=self.directory_summary_persist_dir)

	def set_possessor_research_categories(self, possessor_category_dict: Dict[str, List[str]]):
		r"""
		Set the research categories of the possessors, this research categories is used to recommend proper new papers
		to the possessors.

		Args:
			possessor_category_dict (Dict[str, List[str]]): the research categories to be set.
				It is a dictionary with:

				- key: possessor
				- value: the list of research categories. For details about research categories,
				refer to the class `ArxivCategory`.
		"""
		for possessor in possessor_category_dict.keys():
			dir_id = str((Path(self.paper_root) / possessor).relative_to(self.root))
			self._set_dir_metadata(
				dir_id=dir_id,
				key=DIR_CATEGORY_NAME,
				val=possessor_category_dict[possessor],
			)

	def add_dir(self, directory: str, verbose: bool = False):
		r"""
		Add a directory to the paper storage.
		"""
		if Path(self.paper_root) not in Path(directory).parents:
			raise ValueError("Invalid directory path, please add your documents to the paper warehouse, "
							 "and store them in the PaperStorage first.")
		self._auto_summarize_dir(directory=directory, verbose=verbose)
