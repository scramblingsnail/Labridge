import json

from llama_index.core.llms import LLM
from llama_index.core import Settings
from llama_index.core.embeddings import BaseEmbedding

from labridge.tools.base.function_base_tools import CallBackBaseTool, FuncOutputWithLog
from labridge.tools.base.tool_log import ToolLog, TOOL_OP_DESCRIPTION, TOOL_REFERENCES
from labridge.callback.base.operation_log import OperationOutputLog, OP_DESCRIPTION, OP_REFERENCES
from labridge.interact.authorize.authorize import operation_authorize, aoperation_authorize
from labridge.callback.paper.add_paper import AddNewRecentPaperOperation

from typing import Any


class AddNewRecentPaperTool(CallBackBaseTool):
	r"""
	This tool is used to add a new paper into a specific user's recent papers storage.

	Args:
		llm (LLM): The used LLM. If not specified, the `Settings.llm` will be used.
		embed_model (BaseEmbedding): The used embedding model. If not specified, the `Settings.embed_model` will be used.
		verbose (bool): Whether to show the inner progress.
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
			fn=self.add_paper,
			async_fn=self.a_add_paper,
			tool_name=AddNewRecentPaperTool.__name__,
			callback_operation=AddNewRecentPaperOperation,
		)

	def log(self, **kwargs: Any) -> ToolLog:
		op_log = kwargs["operation_log"]
		if not isinstance(op_log, OperationOutputLog):
			raise ValueError("operation_log must be 'OperationLog'.")
		log_to_user = op_log.log_to_user
		log_to_system = op_log.log_to_system
		return ToolLog(
			tool_name=self.metadata.name,
			log_to_user=log_to_user,
			log_to_system=log_to_system,
		)

	def add_paper(
		self,
		user_id: str,
		paper_file_path: str,
	) -> FuncOutputWithLog:
		r"""
		This tool is used to add a new paper to a specific user's recent papers storage.

		Args:
			user_id (str): The user_id of a lab member.
			paper_file_path (str): The file path of the paper to be added. Browse the chat context or tool logs
				to get the correct and valid file path.

		Returns:
			FuncOutputWithLog: The output and log.
		"""
		# This docstring is used as the tool description.
		op_name = self._callback_operation.__name__
		kwargs = {
			"user_id": user_id,
			"paper_file_path": paper_file_path,
		}

		kwargs_str = json.dumps(kwargs)
		operation_log = operation_authorize(
			user_id=user_id,
			op_name=op_name,
			kwargs_str=kwargs_str,
			llm=self._llm,
			embed_model=self._embed_model,
			verbose=self._verbose,
		)
		log_dict = {"operation_log": operation_log}

		return FuncOutputWithLog(
			fn_output=f"Have Added the paper {paper_file_path} to recent papers of the user {user_id}",
			fn_log=log_dict,
		)

	async def a_add_paper(
		self,
		user_id: str,
		paper_file_path: str,
	) -> FuncOutputWithLog:
		r"""
		This tool is used to add a new paper to a specific user's recent papers storage.

		Args:
			user_id (str): The user_id of a lab member.
			paper_file_path (str): The file path of the paper to be added. Browse the chat context or tool logs
				to get the correct and valid file path.

		Returns:
			FuncOutputWithLog: The output and log.
		"""
		# This docstring is used as the tool description.
		op_name = self._callback_operation.__name__
		kwargs = {
			"user_id": user_id,
			"paper_file_path": paper_file_path,
		}

		kwargs_str = json.dumps(kwargs)
		operation_log = await aoperation_authorize(
			user_id=user_id,
			op_name=op_name,
			kwargs_str=kwargs_str,
			llm=self._llm,
			embed_model=self._embed_model,
			verbose=self._verbose,
		)

		log_dict = {"operation_log": operation_log}
		return FuncOutputWithLog(
			fn_output=f"Have Added the paper {paper_file_path} to recent papers of the user {user_id}",
			fn_log=log_dict,
		)


if __name__ == "__main__":
	from labridge.tools.utils import unpack_tool_output
	from labridge.llm.models import get_models

	llm, embed_model = get_models()

	tt = AddNewRecentPaperTool(
		llm=llm,
		embed_model=embed_model,
	)

	tool_output = tt.call(
		user_id="杨再正",
		paper_file_path="/root/zhisan/Labridge/docs/tmp_papers/杨再正/TorchProbe: Fuzzing Dynamic Deep Learning Compilers.pdf"
	)

	tool_output, tool_log = unpack_tool_output(tool_out_json=tool_output.content)

	print(tool_output)

	tool_log = ToolLog.loads(tool_log)
	print("to user: \n", tool_log.log_to_user)
	print("to system: \n", tool_log.log_to_system)
