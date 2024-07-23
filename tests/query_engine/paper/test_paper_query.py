from llama_index.core import ServiceContext

from labridge.llm.models import get_reranker, get_models
from labridge.custom_query_engine.paper.utils import get_default_paper_query_engines


if __name__ == "__main__":
	llm, embed_model = get_models()
	re_ranker = get_reranker()

	query_engine, sub_query_engine = get_default_paper_query_engines(
		llm=llm,
		embed_model=embed_model,
		re_ranker=re_ranker,
	)

	while True:
		query_input = input("User: ")
		response = query_engine.query(query_input)
		# response = sub_query_engine.query(query_input)
		print(response)
