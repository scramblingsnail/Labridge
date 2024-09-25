from llama_index.core import Settings
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.llms import LLM
from llama_index.core.schema import NodeWithScore, MetadataMode

from labridge.tools.base.tool_log import ToolLog, TOOL_OP_DESCRIPTION, TOOL_REFERENCES
from labridge.tools.base.tool_base import RetrieverBaseTool, TOOL_LOG_REF_INFO_KEY
from labridge.func_modules.reference.paper import PaperInfo
from labridge.func_modules.paper.retrieve.paper_retriever import (
	PaperRetriever,
	PAPER_VECTOR_TOP_K,
	PAPER_SUMMARY_TOP_K,
	PAPER_TOP_K,
	PAPER_RETRIEVE_TOP_K,
)
from labridge.func_modules.paper.retrieve.shared_paper_retrieve import (
	SharedPaperRetriever,

)
from labridge.func_modules.paper.parse.extractors.metadata_extract import (
	PAPER_POSSESSOR,
	PAPER_TITLE,
	PAPER_REL_FILE_PATH,
	PAPER_DOI,
)


from typing import Tuple, List
from pathlib import Path


class SharedPaperRetrieverTool(RetrieverBaseTool):
	r"""
	This tool is used to retrieve in the shared papers storage of the laboratory.

	Multi-level, hybrid retrieving is used for accurate results.
	For details of retrieving, refer to the docstring of `PaperRetriever`.

	Args:
		llm (LLM): The used LLM.
		embed_model (BaseEmbedding): The used embedding model.
		vector_similarity_top_k (int): The top-k of content-based retrieving. Defaults to `PAPER_VECTOR_TOP_K`.
		summary_similarity_top_k (int): The top-k of summary-based retrieving. Defaults tp `PAPER_SUMMARY_TOP_K`.
		docs_top_k (int): The top-k docs will be selected. Defaults to `PAPER_TOP_K`.
		re_retrieve_top_k (int): The top-k of retrieving among the selected `docs_top_k` docs.
			Defaults to `PAPER_RETRIEVE_TOP_K`.
		final_use_context (bool): Whether to use the context nodes of the retrieved nodes as parts of results.
			Defaults to True.
		final_use_summary (bool): Whether to use the summary nodes of the retrieved nodes' relevant docs as parts of results.
			Defaults to True.
	"""
	def __init__(
		self,
		llm: LLM = None,
		embed_model: BaseEmbedding = None,
		vector_similarity_top_k: int = PAPER_VECTOR_TOP_K,
		summary_similarity_top_k: int = PAPER_SUMMARY_TOP_K,
		docs_top_k: int = PAPER_TOP_K,
		re_retrieve_top_k: int = PAPER_RETRIEVE_TOP_K,
		final_use_context: bool = True,
		final_use_summary: bool = True,
	):
		self._llm = llm or Settings.llm
		self._embed_model = embed_model or Settings.embed_model
		paper_retriever = SharedPaperRetriever.from_storage(
			llm=self._llm,
			embed_model=self._embed_model,
		)

		# paper_retriever = PaperRetriever.from_storage(
		# 	llm=self._llm,
		# 	embed_model=self._embed_model,
		# 	vector_similarity_top_k=vector_similarity_top_k,
		# 	summary_similarity_top_k=summary_similarity_top_k,
		# 	docs_top_k=docs_top_k,
		# 	re_retrieve_top_k=re_retrieve_top_k,
		# 	final_use_context=final_use_context,
		# 	final_use_summary=final_use_summary,
		# )
		super().__init__(
			name=SharedPaperRetrieverTool.__name__,
			retriever=paper_retriever,
			retrieve_fn=paper_retriever.retrieve,
		)
		root = Path(__file__)
		for i in range(5):
			root = root.parent
		self.root = root

	def log(self, log_dict: dict) -> ToolLog:
		r""" Return the ToolLog with log string in a specific format. """
		item_to_be_retrieved = log_dict["item_to_be_retrieved"]

		ref_infos: List[PaperInfo] = log_dict.get(TOOL_LOG_REF_INFO_KEY)

		op_log = (
			f"Retrieve in the shared papers.\n"
			f"retrieve string: {item_to_be_retrieved}\n"
		)
		log_to_user = None
		log_to_system = {
			TOOL_OP_DESCRIPTION: op_log,
			TOOL_REFERENCES: [ref_info.dumps() for ref_info in ref_infos]
		}
		return ToolLog(
			tool_name=self.metadata.name,
			log_to_user=log_to_user,
			log_to_system=log_to_system,
		)

	def _retrieve(self, retrieve_kwargs: dict) -> List[NodeWithScore]:
		r""" Use the retriever to retrieve relevant nodes. """
		nodes = self._retriever.retrieve(**retrieve_kwargs)
		return nodes

	async def _aretrieve(self, retrieve_kwargs: dict) -> List[NodeWithScore]:
		r""" Asynchronously use the retriever to retrieve relevant nodes. """
		nodes = await self._retriever.aretrieve(**retrieve_kwargs)
		return nodes

	def get_ref_info(self, nodes: List[NodeWithScore]) -> List[PaperInfo]:
		r"""
		Get the reference paper infos

		Returns:
			List[PaperInfo]: The reference paper infos in answering.
		"""
		doc_ids, doc_titles, doc_possessors = [], [], []
		ref_infos = []
		for node_score in nodes:
			ref_doc_id = node_score.node.ref_doc_id
			if ref_doc_id and ref_doc_id not in doc_ids:
				doc_ids.append(ref_doc_id)
				title = node_score.node.metadata.get(PAPER_TITLE) or ref_doc_id
				possessor = node_score.node.metadata.get(PAPER_POSSESSOR)
				rel_path = node_score.node.metadata.get(PAPER_REL_FILE_PATH)
				doi = node_score.node.metadata.get(PAPER_DOI)
				if rel_path is None:
					raise ValueError("Invalid database.")
				paper_info = PaperInfo(
					title=title,
					possessor=possessor,
					file_path=str(self.root / rel_path),
					doi=doi,
				)
				ref_infos.append(paper_info)
				doc_titles.append(title)
				doc_possessors.append(possessor)
		return ref_infos

	def _nodes_to_tool_output(self, nodes: List[NodeWithScore]) -> Tuple[str, dict]:
		r""" output the retrieved contents in a specific format, and the output log. """
		ref_infos = self.get_ref_info(nodes=nodes)
		log_dict = {
			TOOL_LOG_REF_INFO_KEY: ref_infos,
		}

		paper_contents = {}
		for node in nodes:
			doc_name = node.node.ref_doc_id
			if doc_name not in paper_contents:
				paper_contents[doc_name] = [node.get_content(metadata_mode=MetadataMode.LLM)]
			else:
				paper_contents[doc_name].append(node.get_content(metadata_mode=MetadataMode.LLM))

		if paper_contents:
			content_str = "Have retrieved the following contents: \n"
			contents = []
			for doc_name in paper_contents.keys():
				each_str = f"Following contents are from the paper: {doc_name}:\n"
				each_str += "\n".join(paper_contents[doc_name])
				contents.append(each_str.strip())
			content_str += "\n\n".join(contents)
		else:
			content_str = "Have retrieved nothing.\n"
		return content_str, log_dict


if __name__ == "__main__":
	import asyncio
	from labridge.models.utils import get_models
	from labridge.tools.utils import unpack_tool_output

	llm, embed_model = get_models()

	rr = SharedPaperRetrieverTool(
		llm=llm,
		embed_model=embed_model,
	)

	# tool_output = rr.call(item_to_be_retrieved="PPO algorithm.")
	# tool_output, tool_log = unpack_tool_output(tool_out_json=tool_output.content)
	# tool_log = ToolLog.loads(tool_log)
	#
	# print(tool_output)
	# print("to user: ", tool_log.log_to_user)
	# print("to system: ", tool_log.log_to_system)

	async def main():
		task1 = asyncio.create_task(rr.acall(item_to_be_retrieved="SAC algorithm."))
		task2 = asyncio.create_task(rr.acall(item_to_be_retrieved="TD3 algorithm."))
		task3 = asyncio.create_task(rr.acall(item_to_be_retrieved="PPO algorithm."))
		task4 = asyncio.create_task(rr.acall(item_to_be_retrieved="Deep learning compiler."))

		tool_output1 = await task1
		tool_output2 = await task2
		tool_output3 = await task3
		tool_output4 = await task4

		tool_output, tool_log = unpack_tool_output(tool_out_json=tool_output1.content)
		tool_log = ToolLog.loads(tool_log)

		print(tool_output)
		print("to user: ", tool_log.log_to_user)
		print("to system: ", tool_log.log_to_system)


	asyncio.run(main())
