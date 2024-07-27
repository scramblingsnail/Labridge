import os

from pathlib import Path
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.schema import MetadataMode
from llama_index.core import VectorStoreIndex
from llama_index.core import ServiceContext
from llama_index.core.storage import StorageContext

from labridge.paper.parse.paper_reader import PaperReader
from labridge.llm.models import get_models
from labridge.paper.parse.extractors.source_analyze import PaperSourceAnalyzer


article_list = ["docs/papers/杨再正/存算一体/Fully hardware-implemented memristor CNN.pdf",
		"docs/papers/张三/强化学习/alpha star.pdf",
		"docs/papers/张三/强化学习/Human-level control through deep reinforcement learning.pdf",
		"docs/papers/杨再正/存算一体/"
		"2020 lin peng Three-dimensional memristor circuits as complex networks.pdf",
		"docs/papers/杨再正/存算一体/"
		"2018 NC Efficient and self-adaptive in-situ learning in multilayer memristor neural networks.pdf",
		"docs/papers/杨再正/存算一体/"
		"2019 wangzhongrui In situ training of feed-forward and recurrent convolutional memristor network.pdf",
		"docs/papers/杨再正/存算一体/Reinforcement learning with analogue memristor arrays.pdf", ]

ieee_list = [
	"docs/papers/张三/深度学习编译/The_Deep_Learning_Compiler_A_Comprehensive_Survey.pdf",
	"docs/papers/张三/深度学习编译/"
	"Towards Efficient Generative Large Language Model Serving-A Survey from Algorithms to Systems.pdf",
	"docs/papers/张三/深度学习编译/CIM/"
	"A Compilation Tool for Computation Offloading in ReRAM-based CIM Architectures.pdf",
	"docs/papers/张三/深度学习编译/CIM/"
	"A_Compilation_Framework_for_SRAM_Computing-in-Memory_Systems_With_Optimized_Weight_Mapping_and_Error_Correction.pdf",
	"docs/papers/张三/深度学习编译/CIM/C4CAM_ACompiler for CAM-based In-memory Accelerators.pdf",
	"docs/papers/张三/深度学习编译/CIM/CIM-MLC_AMulti-level Compilation Stack for Computing-in-memory accelerators.pdf", ]


root = Path(__file__)
for i in range(4):
	root = root.parent


def test_paper_source():
	llm, embed_model = get_models()

	for paper in (article_list + ieee_list):
		paper_path = root / paper
		print(f"\n>>> Paper: {paper_path}\n")

		src_analyzer = PaperSourceAnalyzer(llm=llm, keyword_count_threshold=4)
		src = src_analyzer.analyze_source(paper_path=paper_path)
		print(src)

def test_read_single_paper():
	llm, embed_model = get_models()
	ingestion_transformation = [SentenceSplitter(chunk_size=1024, chunk_overlap=256), ]

	rr = PaperReader(llm=llm)

	paper_path = root / article_list[0]
	doc_nodes_1, extra_nodes_1 = rr.read_single_paper(file_path=paper_path)
	for doc_node in doc_nodes_1:
		print("\t>>> ", doc_node.node_id)
		print("\t>>> Excluded metadata in embedding: ", doc_node.excluded_embed_metadata_keys)
		print("\t>>> Excluded metadata in LLM: ", doc_node.excluded_llm_metadata_keys)
		print("\t>>> Metadata in embedding:")
		print("\t>>> ", doc_node.get_content(metadata_mode=MetadataMode.EMBED))
		print("\t>>> Metadata in LLM:")
		print("\t>>> ", doc_node.get_content(metadata_mode=MetadataMode.LLM))


def test_read_papers():
	llm, embed_model = get_models()

	rr = PaperReader(llm=llm)
	paper_files = [root / paper for paper in article_list[:3]]

	nodes_list, extra_nodes_list = rr.read_papers(input_files=paper_files)
	for idx, doc_node in enumerate(nodes_list):
		print(f"=========================================== Paper {idx} ===========================================")
		print(">>> Source: \n", doc_node.node_id)
		print(">>> Metadata: \n", doc_node.metadata)
		print("\n\n>>> Content: \n", doc_node.get_content(metadata_mode=MetadataMode.NONE))


def test_read_directory(paper_dir = None):
	llm, embed_model = get_models()

	rr = PaperReader(llm=llm, recursive=True)
	if paper_dir is None:
		paper_dir = root / "docs/papers/杨再正/存算一体"

	nodes_list, extra_nodes_list = rr.read_papers(input_dir=paper_dir)
	for idx, doc_node in enumerate(nodes_list):
		print(f"=========================================== Paper {idx} ===========================================")
		print(">>> Source: \n", doc_node.node_id)
		print(">>> Metadata: \n", doc_node.metadata)


def test_paper_to_index(input_dirs, persist_dir):
	llm, embed_model = get_models()
	if os.path.exists(persist_dir):
		my_storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
	else:
		my_storage_context = StorageContext.from_defaults(persist_dir=None)
	service_context = ServiceContext.from_defaults(embed_model=embed_model, llm=llm)
	ingestion_transformation = [SentenceSplitter(chunk_size=1024, chunk_overlap=256), ]

	rr = PaperReader(llm=llm, recursive=True)

	for idx, input_dir in enumerate(input_dirs):
		nodes_list, extra_nodes_list = rr.read_papers(input_dir=input_dir, show_progress=True)

		nodes = []
		for src_nodes in nodes_list:
			nodes += [n for n in src_nodes]
		print("nodes num: ", len(nodes))

		vector_index = VectorStoreIndex(nodes, service_context=service_context, storage_context=my_storage_context)
		vector_index.set_index_id(index_id=f"vector_index_{idx + 1}")
		vector_index.storage_context.persist(persist_dir=persist_dir)


if __name__ == "__main__":
	# test_paper_source()
	# test_read_single_paper()
	# test_read_papers()
	test_read_directory()
	#
	# store_dir = root / "storage/papers/杨再正"
	# file_dirs = [
	# 	root / "docs/papers/杨再正/存算一体",
	# 	root / "docs/papers/杨再正/神经网络量化",
	# ]
	# test_paper_to_index(input_dirs=file_dirs, persist_dir=store_dir)
