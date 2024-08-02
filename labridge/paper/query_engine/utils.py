from llama_index.core import ServiceContext

from ...llm.models import get_reranker, get_models
from .paper_query_engine import (
	PaperQueryEngine,
	PaperSubQueryEngine,
)
from ..retrieve.paper_retriever import PaperRetriever


def get_default_paper_query_engines(llm, embed_model, re_ranker=None):
	service_context = ServiceContext.from_defaults(embed_model=embed_model, llm=llm)

	paper_retriever = PaperRetriever.from_storage(
		service_context=service_context,
		vector_similarity_top_k=10,
		summary_similarity_top_k=3,
		docs_top_k=2,
		re_retrieve_top_k=3,
		final_use_context=True,
		final_use_summary=True,
	)

	paper_query_engine = PaperQueryEngine(
		llm=llm,
		paper_retriever=paper_retriever,
		re_ranker=re_ranker,
	)

	paper_sub_query_engine = PaperSubQueryEngine(llm=llm, paper_query_engine=paper_query_engine)
	return paper_query_engine, paper_sub_query_engine, paper_retriever
