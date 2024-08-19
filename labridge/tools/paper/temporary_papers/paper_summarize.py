import json

from llama_index.core import Settings
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.llms import LLM

from labridge.tools.base.function_base_tools import CallBackBaseTool, FuncOutputWithLog
from labridge.tools.base.tool_log import ToolLog, TOOL_OP_DESCRIPTION, TOOL_REFERENCES
from labridge.callback.paper.paper_summarize import PaperSummarizeOperation
from labridge.interact.authorize.authorize import operation_authorize, aoperation_authorize

from typing import Any


class RecentPaperSummarizeTool(CallBackBaseTool):
	r"""
	This tool summarize a recent paper of a user (stored in the RecentPaperStore).

	Args:
		llm (LLM): The used llm.
		embed_model (BaseEmbedding): The used embedding model.
	"""
	def __init__(
		self,
		llm: LLM = None,
		embed_model: BaseEmbedding = None,
		verbose: bool = False,
	):
		self._llm = llm or Settings.llm
		self._embed_model = embed_model or Settings.embed_model
		self._verbose = verbose
		super().__init__(
			fn=self.summarize_paper,
			async_fn=self.asummarize_paper,
			tool_name=RecentPaperSummarizeTool.__name__,
			callback_operation=PaperSummarizeOperation,
			return_direct=True,
		)

	def summarize_paper(
		self,
		user_id: str,
		paper_file_path: str,
	) -> FuncOutputWithLog:
		r"""
		This tool is used to summarize a paper that is stored in a specific user's recent papers storage.
		This tool is used ONLY when the user explicitly ask for a summarization of the paper.
		DO NOT use this tool by yourself.

		Args:
			user_id (str): The user_id of a lab member.
			paper_file_path (str): The file path of a specific paper. Browse the chat context to get the correct
				and valid file path of the paper.

		Returns:
			The summary of the paper.
		"""
		# This docstring is used as the tool description.
		op_name = self._callback_operation.__name__
		kwargs = {"user_id": user_id, "paper_file_path": paper_file_path}
		kwargs_str = json.dumps(kwargs)
		operation_log = operation_authorize(
			user_id=user_id,
			op_name=op_name,
			kwargs_str=kwargs_str,
			llm=self._llm,
			embed_model=self._embed_model,
			verbose=self._verbose,
		)
		fn_output = operation_log.operation_output
		fn_log = {"operation_log": operation_log}
		return FuncOutputWithLog(
			fn_output=fn_output,
			fn_log=fn_log,
		)

	async def asummarize_paper(
		self,
		user_id: str,
		paper_file_path: str,
	) -> FuncOutputWithLog:
		r"""
		This tool is used to summarize a paper that is stored in a specific user's recent papers storage.
		This tool is used ONLY when the user explicitly ask for a summarization of the paper.
		DO NOT use this tool by yourself.

		Args:
			user_id (str): The user_id of a lab member.
			paper_file_path (str): The file path of a specific paper. Browse the chat context to get the correct
				and valid file path of the paper.

		Returns:
			The summary of the paper.
		"""
		# This docstring is used as the tool description.
		op_name = self._callback_operation.__name__
		kwargs = {"user_id": user_id, "paper_file_path": paper_file_path}
		kwargs_str = json.dumps(kwargs)
		operation_log = await aoperation_authorize(
			user_id=user_id,
			op_name=op_name,
			kwargs_str=kwargs_str,
			llm=self._llm,
			embed_model=self._embed_model,
			verbose=self._verbose,
		)
		fn_output = operation_log.operation_output
		fn_log = {"operation_log": operation_log}
		return FuncOutputWithLog(
			fn_output=fn_output,
			fn_log=fn_log,
		)

	def log(self, **kwargs: Any) -> ToolLog:
		paper_file_path = kwargs["paper_file_path"]
		user_id = kwargs["user_id"]
		log_str = f"Summarize the paper {paper_file_path} for the user {user_id}."
		log_to_user = None
		log_to_system = {
			TOOL_OP_DESCRIPTION: log_str,
			TOOL_REFERENCES: None,
		}

		return ToolLog(
			tool_name=self.metadata.name,
			log_to_user=log_to_user,
			log_to_system=log_to_system,
		)


if __name__ == "__main__":
	import asyncio
	from labridge.tools.utils import unpack_tool_output
	from labridge.llm.models import get_models

	llm, embed_model = get_models()

	paper_path = "/root/zhisan/Labridge/docs/tmp_papers/杨再正/Addressing Function Approximation Error in Actor-Critic Methods.pdf"

	ss = RecentPaperSummarizeTool(
		llm=llm,
		embed_model=embed_model,
	)

	# tool_output = ss.call(
	# 	user_id="杨再正",
	# 	paper_file_path=paper_path,
	# )
	# tool_output, tool_log = unpack_tool_output(tool_out_json=tool_output.content)
	# print(tool_output)
	# tool_log = ToolLog.loads(tool_log)
	# print("to user: ", tool_log.log_to_user)
	# print("to system: ", tool_log.log_to_system)

	async def main():
		tool_output = await ss.acall(
			user_id="杨再正",
			paper_file_path=paper_path,
		)

		tool_output, tool_log = unpack_tool_output(tool_out_json=tool_output.content)
		print(tool_output)
		tool_log = ToolLog.loads(tool_log)
		print("to user: ", tool_log.log_to_user)
		print("to system: ", tool_log.log_to_system)

	asyncio.run(main())



