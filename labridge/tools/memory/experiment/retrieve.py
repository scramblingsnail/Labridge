import os.path

from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.schema import NodeWithScore, MetadataMode

from labridge.func_modules.memory.experiment.retrieve_log import ExperimentLogRetriever
from labridge.func_modules.memory.experiment.experiment_log import EXPERIMENT_LOG_ATTACHMENT_KEY
from labridge.func_modules.memory.base import LOG_DATE_NAME, LOG_TIME_NAME
from labridge.tools.base.tool_base import RetrieverBaseTool, TOOL_LOG_REF_INFO_KEY
from labridge.tools.base.tool_log import ToolLog, TOOL_OP_DESCRIPTION, TOOL_REFERENCES
from labridge.func_modules.reference.experiment_log import ExperimentLogRefInfo

from typing import List, Tuple


class ExperimentLogRetrieveTool(RetrieverBaseTool):
	r"""
	This tool is used to retrieve the relevant experiment log in the user's experiment log storage.
	The tool description is set as the docstring of the method `retrieve` of the `retriever`.

	Args:
		embed_model (BaseEmbedding): The used embedding model. If not specified, the `Setting.embed_model` will be used.
		final_use_context (bool): Whether to add the context nodes to the final retrieving results.
		relevant_top_k (int): The top-k relevant nodes will be used as the retrieved results.
	"""
	def __init__(
		self,
		embed_model: BaseEmbedding = None,
		final_use_context: bool = True,
		relevant_top_k: int = None,
	):
		retriever = ExperimentLogRetriever(
			embed_model=embed_model,
			final_use_context=final_use_context,
			relevant_top_k=relevant_top_k,
		)
		super().__init__(
			name=ExperimentLogRetrieveTool.__name__,
			retriever=retriever,
			retrieve_fn=retriever.retrieve,
		)

	def log(self, log_dict: dict) -> ToolLog:
		r"""
		Record the tool log.

		Args:
			log_dict (dict): Including the input keyword arguments and the (output, log) of retrieving.

		Returns:
			The tool log.
		"""
		user_id = log_dict["memory_id"]
		item_to_be_retrieved = log_dict["item_to_be_retrieved"]
		start_date = log_dict.get("start_date", None)
		end_date = log_dict.get("end_date", None)

		ref_infos: List[ExperimentLogRefInfo] = log_dict.get(TOOL_LOG_REF_INFO_KEY)

		log_string = (
			f"Retrieve in the experiment log memory of the user: {user_id}.\n"
			f"retrieve string: {item_to_be_retrieved}\n"
		)
		if None not in [start_date, end_date]:
			log_string += (
				f"start_date: {start_date}\n"
				f"end_date: {end_date}"
			)

		log_to_user = None
		log_to_system = {
			TOOL_OP_DESCRIPTION: log_string,
			TOOL_REFERENCES: [ref_info.dumps() for ref_info in ref_infos],
		}
		return ToolLog(
			log_to_user=log_to_user,
			log_to_system=log_to_system,
			tool_name=self.metadata.name,
		)

	def get_ref_info(self, nodes: List[NodeWithScore]) -> List[ExperimentLogRefInfo]:
		r"""
		Get the reference paper infos

		Returns:
			List[PaperInfo]: The reference paper infos in answering.
		"""
		ref_infos = []
		for node_score in nodes:
			metadata = node_score.node.metadata
			log_str = node_score.node.text
			experiment_name = node_score.node.parent_node.node_id
			attachment_path = metadata.get(EXPERIMENT_LOG_ATTACHMENT_KEY, None)
			date = metadata.get(LOG_DATE_NAME)
			h_m_s = metadata.get(LOG_TIME_NAME)
			log_ref_info = ExperimentLogRefInfo(
				date_time=f"{date} {h_m_s}",
				log_str=log_str,
				attachment_path=attachment_path,
				experiment_name=experiment_name,
			)
			ref_infos.append(log_ref_info)
		return ref_infos

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
		expr_nodes_dict = {}

		ref_infos = self.get_ref_info(nodes=nodes)
		log_dict = {
			TOOL_LOG_REF_INFO_KEY: ref_infos,
		}

		for node in nodes:
			expr_node = node.node.parent_node
			if expr_node is not None:
				if expr_node.node_id not in expr_nodes_dict.keys():
					expr_nodes_dict[expr_node.node_id] = [node]
				else:
					expr_nodes_dict[expr_node.node_id].append(node)

		if expr_nodes_dict:
			msg = "Have retrieved the following experiment logs:"
			contents = [msg]
			for expr_name in expr_nodes_dict.keys():
				msg = f"The following logs are from the experiment: {expr_name}"
				contents.append(msg)
				for idx, node in enumerate(expr_nodes_dict[expr_name]):
					content_str = (
						f"Log {idx + 1}:\n"
						f"{node.node.get_content(metadata_mode=MetadataMode.LLM)}"
					)
					contents.append(content_str.strip())
			output_str = "\n\n".join(contents)
		else:
			output_str = "Have retrieved nothing relevant."
		return output_str, log_dict


if __name__ == "__main__":
	import asyncio
	from labridge.models.utils import get_models
	from labridge.tools.utils import unpack_tool_output
	from labridge.tools.utils import get_ref_file_paths, get_extra_str_to_user

	llm, embed_model = get_models()

	log_retrieve_tool = ExperimentLogRetrieveTool(
		embed_model=embed_model,
	)

	tool_output = log_retrieve_tool.call(
		item_to_be_retrieved="光刻参数",
		memory_id="杨再正",
		start_date="2024-8-18",
		end_date="2024-9-7",
	)

	tool_output, tool_log = unpack_tool_output(tool_output.content)
	print(tool_output)

	log = ToolLog.loads(tool_log)

	paths = get_ref_file_paths(tool_logs=[log])
	log_to_user = get_extra_str_to_user(tool_logs=[log])
	print(paths)
	print(log_to_user)

	# print("To user: ", log.log_to_user)
	# print("To system: ", log.log_to_system)
	# print(os.path.exists(r"D:\python_works\Labridge\documents\experiment_files\杨再正\2024-09-09/Server-Client.md"))

	# async def main():
	# 	tool_output = await log_retrieve_tool.acall(
	# 	item_to_be_retrieved="光刻参数",
	# 	memory_id="杨再正",
	# 	start_date="2024-8-19",
	# 	end_date="2024-8-19",
	# )
	#
	# 	tool_output, tool_log = unpack_tool_output(tool_output.content)
	# 	print(tool_output)
	# 	print(ToolLog.loads(tool_log))
	#
	# asyncio.run(main())


