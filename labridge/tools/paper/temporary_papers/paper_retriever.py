import json

from llama_index.core import Settings
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.llms import LLM
from llama_index.core.schema import NodeWithScore, TextNode, MetadataMode

from labridge.tools.base.tool_base import RetrieverBaseTool
from labridge.tools.base.tool_log import ToolLog, TOOL_OP_DESCRIPTION, TOOL_REFERENCES
from labridge.paper.retrieve.temporary_paper_retriever import (
	RecentPaperRetriever,
	RECENT_PAPER_SIMILARITY_TOP_K,
	RECENT_PAPER_INFO_SIMILARITY_TOP_K,
)


from typing import Any, cast, List, Tuple


class RecentPaperRetrieveTool(RetrieverBaseTool):
	r"""
	This tool is used to retrieve in the recent papers store of a specific user.
	A multilevel retrieving strategy is used. For details, refer to the `RecentPaperRetriever`.
	(start_date, end_date) can be provided to confine the retrieving range.

	Args:
		embed_model (BaseEmbedding): The used embedding model. If not specified, The `Settings.embed_model` will be used.
		first_top_k (int): The similarity_top_k in the first retrieving.
			Defaults to `RECENT_PAPER_INFO_SIMILARITY_TOP_K`.
		secondary_top_k (int): The similarity_top_k in the secondary retrieving.
			Defaults to `RECENT_PAPER_SIMILARITY_TOP_K`.
	"""
	def __init__(
		self,
		embed_model: BaseEmbedding = None,
		first_top_k: int = RECENT_PAPER_INFO_SIMILARITY_TOP_K,
		secondary_top_k: int = RECENT_PAPER_SIMILARITY_TOP_K,
		use_context: bool = False,

	):
		retriever = RecentPaperRetriever(
			embed_model=embed_model,
			final_use_context=use_context,
			first_top_k=first_top_k,
			secondary_top_k=secondary_top_k,
		)
		super().__init__(
			name=RecentPaperRetrieveTool.__name__,
			retriever=retriever,
			retrieve_fn=retriever.retrieve,
		)

	def log(self, log_dict: dict) -> ToolLog:
		r"""
		Record the tool log.

		Args:
			log_dict (dict): Including the input keyword arguments and the retrieving logs.

		Returns:
			ToolLog: The packed tool log.
		"""
		user_id = log_dict["user_id"]
		item_to_be_retrieved = log_dict["item_to_be_retrieved"]
		paper_file_path = log_dict.get("paper_file_path", None)
		start_date = log_dict.get("start_date", None)
		end_date = log_dict.get("end_date", None)

		op_log = (
			f"Retrieve in the recent papers of the user: {user_id}.\n"
			f"retrieve string: {item_to_be_retrieved}\n"
		)
		if paper_file_path is not None:
			op_log += f"target paper file path: {paper_file_path}\n"
		if None not in [start_date, end_date]:
			op_log += (
				f"start_date: {start_date}\n"
				f"end_date: {end_date}"
			)

		log_to_user = None
		log_to_system = {
			TOOL_OP_DESCRIPTION: op_log,
			TOOL_REFERENCES: None,
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

	def _nodes_to_tool_output(self, nodes: List[NodeWithScore]) -> Tuple[str, dict]:
		r""" output the retrieved contents in a specific format, and the output log. """
		paper_contents = {}

		for node in nodes:
			file_path = node.node.parent_node.node_id
			if file_path not in paper_contents:
				paper_contents[file_path] = [node.get_content(metadata_mode=MetadataMode.LLM)]
			else:
				paper_contents[file_path].append(node.get_content(metadata_mode=MetadataMode.LLM))

		if paper_contents:
			content_str = "Have retrieved the following content: \n"
			contents = []
			for paper_path in paper_contents.keys():
				each_str = f"Following contents are from the paper stored in {paper_path}:\n"
				each_str += "\n".join(paper_contents[paper_path])
				contents.append(each_str.strip())
			content_str += "\n\n".join(contents)
		else:
			content_str = "Have retrieved nothing.\n"
		return content_str, dict()


if __name__ == "__main__":
	import asyncio
	from labridge.llm.models import get_models
	from labridge.tools.base.tool_log import ToolLog
	from labridge.tools.utils import unpack_tool_output

	llm, embed_model = get_models()
	pp = RecentPaperRetrieveTool(
		embed_model=embed_model,
		use_context=True,
	)

	# tool_output = pp.call(item_to_be_retrieved="deep learning compiler", user_id="杨再正", )
	# tool_output, tool_log = unpack_tool_output(tool_out_json=tool_output.content)
	# print(tool_output)
	# tool_log = ToolLog.loads(tool_log)
	# print("to user: ", tool_log.log_to_user)
	# print("to system: ", tool_log.log_to_system)


	async def main():
		task1 = asyncio.create_task(
			pp.acall(item_to_be_retrieved="deep learning compiler", user_id="杨再正",)
		)

		task2 = asyncio.create_task(
			pp.acall(item_to_be_retrieved="memristor", user_id="杨再正",)
		)

		tool_output1 = await task1
		tool_output2 = await task2


		tool_output, tool_log = unpack_tool_output(tool_out_json=tool_output2.content)
		print(tool_output)
		tool_log = ToolLog.loads(tool_log)
		print("to user: ", tool_log.log_to_user)
		print("to system: ", tool_log.log_to_system)

	asyncio.run(main())
