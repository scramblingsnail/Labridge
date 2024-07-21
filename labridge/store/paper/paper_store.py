import os

from typing import Optional, Tuple, List, Union
from pathlib import Path

from llama_index.core.indices.document_summary import DocumentSummaryIndex
from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.storage import StorageContext
from llama_index.core.schema import Document, TransformComponent
from llama_index.core import load_index_from_storage
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
from llama_index.core.service_context import ServiceContext

from ...parse.paper.parsers.base import MAINTEXT, METHODS, CONTENT_TYPE_NAME
from ...prompt.store import PAPER_SUMMARIZE_QUERY, DIR_SUMMARIZE_QUERY, METHODS_SUMMARIZE_QUERY


PAPER_VECTOR_INDEX_ID = "vector_index"
PAPER_SUMMARY_INDEX_ID = "paper_summary_index"

SummarizeQueries = {
	MAINTEXT: PAPER_SUMMARIZE_QUERY,
	METHODS: METHODS_SUMMARIZE_QUERY,
}

DEFAULT_PAPER_VECTOR_PERSIST_DIR = "storage/papers/vector_index"
DEFAULT_PAPER_SUMMARY_PERSIST_DIR = "storage/papers/paper_summary_index"


class PaperStorage:
	r"""
	TODO: Docstring.
	Store papers.
	1. Vector Index
	2. Summary Index
	Note: they can not share the storage context.
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
				 dir_summary_query: str = DIR_SUMMARIZE_QUERY,
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
		self.dir_summary_query = dir_summary_query
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

	def _get_origin_dir(self, docs: List[Document]) -> Path:
		r"""
		Get the origin directory of the documents.

		Args:
			docs: (Sequence[Document]): Assume the doc id is: `{file_path}_{content_type}`,
				where the file path is relative to the root. The doc format is PDF.

		Returns:
			origin_dir: the origin directory.
		"""
		origin_dir = None
		for doc in docs:
			rel_path = doc.doc_id.split('.pdf')[0] + '.pdf'
			f_path = self.root / rel_path
			if not f_path.exists():
				raise ValueError("The doc id should be '{file_path}_{content_type}', "
								 "the file_path is relative to the package root.")
			if origin_dir is None:
				origin_dir = f_path.parent
			if len(str(origin_dir)) < len(str(f_path.parent)):
				origin_dir = f_path.parent
		return origin_dir

	def _dfs_summarize(self, docs: List[Document], paper_summary_index: DocumentSummaryIndex):
		r""" DFS and summarize each directory. """
		origin_dir = self._get_origin_dir(docs)

		def dfs(current_dir):
			if not current_dir.is_dir():
				return

			for child in current_dir.iterdir():
				if child.is_dir():
					dfs(child)

			child_summaries = []
			for child in current_dir.iterdir():
				if child.is_dir():
					child_id = str(child.relative_to(self.root))
				else:
					child_id = str(child.relative_to(self.root)) + f'_{MAINTEXT}'
				summary = paper_summary_index.get_document_summary(doc_id=child_id)
				child_summaries.append(summary)

			# TODO: Summarize these child summaries and store into the index_struct of a new DocumentSummaryIndex.
			# TODO: This Index is used to find a proper directory when adding a new paper,


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
					 dir_summary_query: str = DIR_SUMMARIZE_QUERY,
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
			dir_summary_query=dir_summary_query,
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
