from llama_index.core.service_context import ServiceContext

from labridge.paper.store.paper_store import PaperDirectorySummaryStore
from labridge.llm.models import get_models
from llama_index.core.schema import MetadataMode


def show_dir_summaries():
	dir_id_to_summary_id = paper_storage.directory_summary_index._index_struct.doc_id_to_summary_id
	print(dir_id_to_summary_id)

	for doc_id in dir_id_to_summary_id.keys():
		print(">>> ", doc_id)
		summary_id = dir_id_to_summary_id[doc_id]
		dir_summary_node = paper_storage.directory_summary_index.docstore.get_node(summary_id)
		print(dir_summary_node.get_content(metadata_mode=MetadataMode.LLM), "\n")


if __name__ == "__main__":
	llm, embed_model = get_models()
	service_context = ServiceContext.from_defaults(llm=llm, embed_model=embed_model)

	paper_storage = PaperDirectorySummaryStore(
		llm=llm,
		embed_model=embed_model,
		service_context=service_context,
	)

	show_dir_summaries()
	# paper_storage.update({"docs/papers/张三": "Test MANUALLY set fields."})

	# new_paper_path = "/root/zhisan/Labridge/docs/papers/张三/深度学习编译/The_Deep_Learning_Compiler_A_Comprehensive_Survey.pdf"
	# paper_storage.match_directory_for_new_paper(pdf_path=new_paper_path, possessor="张三", verbose=True)




