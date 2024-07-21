from llama_index.core import ServiceContext

from ...llm.models import get_reranker, get_models
from ...custom_query_engine.paper.paper_query_engine import (
	PaperQueryEngine,
	PaperSubQueryEngine,
	PaperDetailQueryEngine,
	PaperSummaryQueryEngine
)
from ...retrieve.paper.paper_retriever import (
	PaperDetailRetriever,
	PaperSummaryRetriever
)


def get_default_paper_query_engines(llm, embed_model, re_ranker):
	service_context = ServiceContext.from_defaults(embed_model=embed_model, llm=llm)

	paper_detail_retriever = PaperDetailRetriever.from_storage(service_context=service_context)
	paper_summary_retriever = PaperSummaryRetriever.from_storage(service_context=service_context)

	paper_detail_query_engine = PaperDetailQueryEngine(
		llm=llm,
		paper_detail_retriever=paper_detail_retriever,
		re_ranker=re_ranker,
	)

	paper_summary_query_engine = PaperSummaryQueryEngine(
		llm=llm,
		paper_summary_retriever=paper_summary_retriever,
		re_ranker=re_ranker,
	)

	paper_query_engine = PaperQueryEngine(
		llm=llm,
		paper_detail_query_engine=paper_detail_query_engine,
		paper_summary_query_engine=paper_summary_query_engine,
	)

	paper_sub_query_engine = PaperSubQueryEngine(llm=llm, paper_query_engine=paper_query_engine)
	return paper_query_engine, paper_sub_query_engine
