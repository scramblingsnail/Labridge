
from pathlib import Path
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import MetadataMode
from llama_index.core import VectorStoreIndex
from llama_index.core import ServiceContext
from llama_index.core.tools.query_engine import QueryEngineTool
from llama_index.core.agent.react.formatter import ReActChatFormatter
from llama_index.core.query_engine.retriever_query_engine import RetrieverQueryEngine
from llama_index.core.storage import StorageContext
from llama_index.core.agent.react.base import ReActAgent
from llama_index.core.indices.document_summary.base import DocumentSummaryRetrieverMode

from labridge.parse.paper.paper_reader import PaperReader
from labridge.store.paper.paper_store import PaperStorage, PAPER_VECTOR_INDEX_ID, PAPER_SUMMARY_INDEX_ID
from labridge.llm.models import get_models
from labridge.custom_query_engine.query_engines import SingleQueryEngine
from labridge.prompt.chat import KB_REACT_CHAT_SYSTEM_HEADER, ZH_CHAT_MOTIVATION_TMPL



article_list = [
	"docs/papers/张三/深度学习编译/CIM/"
	"A Compilation Tool for Computation Offloading in ReRAM-based CIM Architectures.pdf",
	"docs/papers/张三/深度学习编译/The_Deep_Learning_Compiler_A_Comprehensive_Survey.pdf",
	"docs/papers/张三/深度学习编译/"
	"Towards Efficient Generative Large Language Model Serving-A Survey from Algorithms to Systems.pdf",
	"docs/papers/张三/深度学习编译/CIM/"
	"A_Compilation_Framework_for_SRAM_Computing-in-Memory_Systems_With_Optimized_Weight_Mapping_and_Error_Correction.pdf",
	"docs/papers/张三/深度学习编译/CIM/C4CAM_ACompiler for CAM-based In-memory Accelerators.pdf",
	"docs/papers/张三/深度学习编译/CIM/CIM-MLC_AMulti-level Compilation Stack for Computing-in-memory accelerators.pdf",
	"docs/papers/张三/强化学习/"
	"off-policy_TD3_twin-deplayed-ddpg_Addressing Function Approximation Error in Actor-Critic Methods.pdf",
	"docs/papers/张三/强化学习/PPO.pdf",
	"docs/papers/张三/强化学习/SAC_second_edition.pdf",
	"docs/papers/张三/强化学习/alpha star.pdf",
]

root = Path(__file__)
for i in range(4):
	root = root.parent

vector_persist_dir = root / "storage/papers/vector_index"
paper_summary_persist_dir = root / "storage/papers/paper_summary_index"

llm, embed_model = get_models()
service_context = ServiceContext.from_defaults(embed_model=embed_model, llm=llm)


def load_index(vector_dir, paper_summary_dir):
	store = PaperStorage.from_storage(vector_persist_dir=str(vector_dir),
									  paper_summary_persist_dir=str(paper_summary_dir),
									  service_context=service_context)
	# doc_ids = list(store.paper_summary_index.docstore.get_all_ref_doc_info().keys())
	# print(store.paper_summary_index.get_document_summary(doc_ids[0])
	return store

def test_read_store_paper():
	rr = PaperReader(llm=llm)
	paper_files = [root / paper for paper in article_list[:]]
	docs, extra_docs = rr.read_papers(input_files=paper_files[1:])

	for doc in docs:
		print(f'>>> {doc.doc_id}')

	if vector_persist_dir.exists() and paper_summary_persist_dir.exists():
		store = load_index(vector_persist_dir, paper_summary_persist_dir)
		print("index loaded.")
		store.insert(paper_docs=docs, extra_docs=extra_docs)
	else:
		store = PaperStorage(docs=docs, extra_docs=extra_docs, service_context=service_context)

	doc_ids = list(store.paper_summary_index.docstore.get_all_ref_doc_info().keys())
	print(doc_ids)
	print(store.paper_summary_index.get_document_summary(doc_ids[-1]))
	store.persist()


def chat():
	store = load_index(vector_persist_dir, paper_summary_persist_dir)

	motivation_engine = SingleQueryEngine(llm=llm, prompt_tmpl=ZH_CHAT_MOTIVATION_TMPL)
	motivation_engine_tool = QueryEngineTool.from_defaults(query_engine=motivation_engine, name="motivation_analyzer",
														   description="这个工具用于分析用户输入内容的动机。")
	# react chat formatter
	retriever_1 = store.vector_index.as_retriever()
	query_engine_1 = RetrieverQueryEngine.from_args(retriever=retriever_1, service_context=service_context)
	query_tool_description_1 = "这个工具用于检索相关的文献文本内容。"
	query_engine_tool_1 = QueryEngineTool.from_defaults(query_engine=query_engine_1, name="resume_retriever_1",
													  description=query_tool_description_1)

	retriever_2 = store.paper_summary_index.as_retriever(retriever_mode=DocumentSummaryRetrieverMode.EMBEDDING,
														 similarity_top_k=3)
	query_engine_2 = RetrieverQueryEngine.from_args(retriever=retriever_2, service_context=service_context)
	query_tool_description_2 = "这个工具用于检索每篇文献的总结。"
	query_engine_tool_2 = QueryEngineTool.from_defaults(query_engine=query_engine_2, name="resume_retriever_2",
														description=query_tool_description_2)

	react_chat_formatter = ReActChatFormatter.from_defaults(system_header=KB_REACT_CHAT_SYSTEM_HEADER)
	chat_engine = ReActAgent.from_tools(tools=[motivation_engine_tool, query_engine_tool_1, query_engine_tool_2],
										react_chat_formatter=react_chat_formatter, verbose=True,
										llm=service_context.llm)

	# for key in store.paper_summary_index._index_struct.doc_id_to_summary_id.keys():
	# 	print(">>> doc: ", key)
	# 	val = store.paper_summary_index._index_struct.doc_id_to_summary_id[key]
	# 	print(">>> val ", val)

	while True:
		text_input = input("User: ")
		if text_input == "exit":
			break

		# v_nodes = retriever_1.retrieve(text_input)

		# print('>>> vector retrieve.')
		# for node in v_nodes:
		# 	print(node.node.ref_doc_id)

		print('>>> summary retrieve.')
		s_nodes = retriever_2.retrieve(text_input)
		for node in s_nodes:
			print(node.node.ref_doc_id)

		# response = chat_engine.chat(message=text_input)
		# print("Agent: {}".format(response))
		#
		# # record and refresh memory.
		# all_messages = chat_engine.memory.get_all()
		# if len(all_messages) > 1:
		# 	# for msg in all_messages:
		# 	chat_engine.memory.set([])

if __name__ == "__main__":
	# test_read_store_paper()
	# load_index()
	chat()

