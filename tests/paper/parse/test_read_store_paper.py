
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

from labridge.func_modules.paper.parse.paper_reader import PaperReader
from labridge.func_modules.paper.store.paper_store import PaperStorage, PAPER_VECTOR_INDEX_ID, PAPER_SUMMARY_INDEX_ID
from labridge.models.utils import get_models
from labridge.common.query_engine.query_engines import SingleQueryEngine



article_list = [
	"documents/papers/杨再正/存算一体/Effective Random Test Generation for Deep Learning Compilers.pdf",
	"documents/papers/杨再正/存算一体/Chaotic memristor.pdf"
	"documents/papers/张三/深度学习编译/"
	"TorchProbe: Fuzzing Dynamic Deep Learning Compilers.pdf"
	"documents/papers/张三/深度学习编译/CIM/"
	"A Compilation Tool for Computation Offloading in ReRAM-based CIM Architectures.pdf",
	"documents/papers/张三/深度学习编译/The_Deep_Learning_Compiler_A_Comprehensive_Survey.pdf",
	"documents/papers/张三/深度学习编译/"
	"Towards Efficient Generative Large Language Model Serving-A Survey from Algorithms to Systems.pdf",
	"documents/papers/张三/深度学习编译/CIM/"
	"A_Compilation_Framework_for_SRAM_Computing-in-Memory_Systems_With_Optimized_Weight_Mapping_and_Error_Correction.pdf",
	"documents/papers/张三/深度学习编译/CIM/C4CAM_ACompiler for CAM-based In-memory Accelerators.pdf",
	"documents/papers/张三/深度学习编译/CIM/CIM-MLC_AMulti-level Compilation Stack for Computing-in-memory accelerators.pdf",
	"documents/papers/张三/强化学习/"
	"off-policy_TD3_twin-deplayed-ddpg_Addressing Function Approximation Error in Actor-Critic Methods.pdf",
	"documents/papers/张三/强化学习/PPO.pdf",
	"documents/papers/张三/强化学习/SAC_second_edition.pdf",
	"documents/papers/张三/强化学习/alpha star.pdf",
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
	docs, extra_docs = rr.read_papers(input_files=paper_files[:])

	for doc in docs:
		print(f'>>> {doc.doc_id}')

	if vector_persist_dir.exists() and paper_summary_persist_dir.exists():
		store = load_index(vector_persist_dir, paper_summary_persist_dir)
		print("index loaded.")
		print("Start insert")
		store.insert(paper_docs=docs, extra_docs=extra_docs)
	else:
		store = PaperStorage(docs=docs, extra_docs=extra_docs, service_context=service_context)

	doc_ids = list(store.paper_summary_index.docstore.get_all_ref_doc_info().keys())
	print(doc_ids)
	print(store.paper_summary_index.get_document_summary(doc_ids[-1]))
	# store.persist()


if __name__ == "__main__":
	test_read_store_paper()
	# load_index()

