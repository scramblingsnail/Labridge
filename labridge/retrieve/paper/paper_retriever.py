from pathlib import Path
from typing import List, Optional, Union

from llama_index.core import VectorStoreIndex
from llama_index.core import ServiceContext
from llama_index.core.storage import StorageContext
from llama_index.core.indices.document_summary.base import DocumentSummaryRetrieverMode
from llama_index.core.retrievers import BaseRetriever, VectorIndexRetriever
from llama_index.core.indices.document_summary.retrievers import DocumentSummaryIndexEmbeddingRetriever
from llama_index.core import QueryBundle
from llama_index.core.schema import NodeWithScore
from llama_index.core import load_index_from_storage

from ...store.paper.paper_store import (
	DEFAULT_PAPER_VECTOR_PERSIST_DIR,
	DEFAULT_PAPER_SUMMARY_PERSIST_DIR,
	PAPER_VECTOR_INDEX_ID,
	PAPER_SUMMARY_INDEX_ID,
)


class PaperSummaryRetriever(BaseRetriever):
	r"""
	TODO: Docstring
	"""
	def __init__(self,
				 paper_summary_retriever: DocumentSummaryIndexEmbeddingRetriever):
		self.paper_summary_retriever = paper_summary_retriever
		super().__init__()

	def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
		summary_chunk_nodes = self.paper_summary_retriever.retrieve(query_bundle)

		doc_ids = set()
		for node in summary_chunk_nodes:
			doc_ids.add(node.node.ref_doc_id)

		summary_nodes = []

		for doc_id in doc_ids:
			doc_id_to_summary_id = self.paper_summary_retriever._index._index_struct.doc_id_to_summary_id
			if doc_id in doc_id_to_summary_id.keys():
				summary_id = doc_id_to_summary_id[doc_id]
				summary_node = self.paper_summary_retriever._index.docstore.get_node(summary_id)
				summary_nodes.append(summary_node)

		second_index = VectorStoreIndex(
			nodes=summary_nodes,
			embed_model=self.paper_summary_retriever._embed_model)
		second_retriever = second_index.as_retriever(similarity_top_k=1)
		final_nodes = second_retriever.retrieve(query_bundle)
		return final_nodes

	@classmethod
	def from_storage(cls,
					 paper_summary_persist_dir: Optional[Union[Path, str]] = None,
					 summary_similarity_top_k: Optional[int] = 3,
					 service_context: Optional[ServiceContext] = None):
		root = Path(__file__)
		for i in range(4):
			root = root.parent

		paper_summary_persist_dir = paper_summary_persist_dir or root / DEFAULT_PAPER_SUMMARY_PERSIST_DIR
		paper_summary_storage_context = StorageContext.from_defaults(persist_dir=paper_summary_persist_dir)

		paper_summary_index = load_index_from_storage(
			storage_context=paper_summary_storage_context,
			index_id=PAPER_SUMMARY_INDEX_ID,
			service_context=service_context)
		summary_retriever = paper_summary_index.as_retriever(
			retriever_mode=DocumentSummaryRetrieverMode.EMBEDDING,
			similarity_top_k=summary_similarity_top_k)
		return cls(paper_summary_retriever=summary_retriever)

class PaperDetailRetriever(BaseRetriever):
	r"""
	TODO: Docstring
	"""
	def __init__(self,
				 paper_vector_retriever: VectorIndexRetriever,
				 paper_summary_retriever: DocumentSummaryIndexEmbeddingRetriever):
		self.paper_vector_retriever = paper_vector_retriever
		self.paper_summary_retriever = paper_summary_retriever
		super().__init__()


	def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
		vector_nodes = self.paper_vector_retriever.retrieve(query_bundle)
		summary_nodes = self.paper_summary_retriever.retrieve(query_bundle)

		doc_ids = set()
		for node in vector_nodes + summary_nodes:
			doc_ids.add(node.node.ref_doc_id)
		print(">>> hybrid docs: \n", doc_ids)
		# constrain search range.
		self.paper_vector_retriever._doc_ids = list(doc_ids)
		hybrid_nodes = self.paper_vector_retriever.retrieve(query_bundle)
		# reset
		self.paper_vector_retriever._doc_ids = None
		return hybrid_nodes

	@classmethod
	def from_storage(cls,
					 vector_persist_dir: Optional[Union[Path, str]] = None,
					 paper_summary_persist_dir: Optional[Union[Path, str]] = None,
					 vector_similarity_top_k: Optional[int] = 10,
					 summary_similarity_top_k: Optional[int] = 3,
					 service_context: Optional[ServiceContext] = None):
		root = Path(__file__)
		for i in range(4):
			root = root.parent

		vector_persist_dir = vector_persist_dir or root / DEFAULT_PAPER_VECTOR_PERSIST_DIR
		paper_summary_persist_dir = paper_summary_persist_dir or root / DEFAULT_PAPER_SUMMARY_PERSIST_DIR
		vector_storage_context = StorageContext.from_defaults(persist_dir=vector_persist_dir)
		paper_summary_storage_context = StorageContext.from_defaults(persist_dir=paper_summary_persist_dir)

		vector_index = load_index_from_storage(
			storage_context=vector_storage_context,
			index_id=PAPER_VECTOR_INDEX_ID,
			service_context=service_context)
		paper_summary_index = load_index_from_storage(
			storage_context=paper_summary_storage_context,
			index_id=PAPER_SUMMARY_INDEX_ID,
			service_context=service_context)

		vector_retriever = vector_index.as_retriever(similarity_top_k=vector_similarity_top_k)
		summary_retriever = paper_summary_index.as_retriever(
			retriever_mode=DocumentSummaryRetrieverMode.EMBEDDING,
			similarity_top_k=summary_similarity_top_k)
		return cls(
			paper_vector_retriever=vector_retriever,
			paper_summary_retriever=summary_retriever,
		)
