from llama_index.core import ServiceContext

from labridge.llm.models import get_models
from labridge.paper.query_engine.utils import get_default_paper_query_engines


if __name__ == "__main__":
	llm, embed_model = get_models()

	query_engine, sub_query_engine, _ = get_default_paper_query_engines(
		llm=llm,
		embed_model=embed_model,
		re_ranker=None,
	)

	while True:
		query_input = input("User: ")
		response = query_engine.query(query_input)
		# response = sub_query_engine.query(query_input)
		print(response)
