from llama_index.core import ServiceContext

from labridge.llm.models import get_reranker, get_models
from labridge.synthesizer.paper.output_parser import paper_query_output_parser
from labridge.custom_query_engine.paper.paper_query_engine import (
	PaperQueryEngine,
	PaperSubQueryEngine,
	PaperDetailQueryEngine,
	PaperSummaryQueryEngine
)
from labridge.retrieve.paper.paper_retriever import (
	PaperDetailRetriever,
	PaperSummaryRetriever
)


def get_query_engine(llm, embed_model, re_ranker):
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
	return paper_query_engine

def get_sub_queries_engine(llm, paper_query_engine):
	paper_sub_query_engine = PaperSubQueryEngine(llm=llm, paper_query_engine=paper_query_engine)
	return paper_sub_query_engine



if __name__ == "__main__":
	llm, embed_model = get_models()
	re_ranker = get_reranker()
	query_engine = get_query_engine(llm=llm, embed_model=embed_model, re_ranker=re_ranker)
	sub_query_engine = get_sub_queries_engine(llm=llm, paper_query_engine=query_engine)

	while True:
		query_input = input("User: ")
		# response = query_engine.query(query_input)
		response = sub_query_engine.query(query_input)
		print(response)
