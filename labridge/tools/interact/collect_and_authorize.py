import json

from llama_index.core.llms import LLM
from llama_index.core import Settings
from llama_index.core.embeddings import BaseEmbedding

from labridge.tools.base.function_base_tools import FuncOutputWithLog, CallBackBaseTool
from labridge.interact.authorize.authorize import operation_authorize, aoperation_authorize
from labridge.callback.base.operation_base import CallBackOperationBase
from labridge.interact.collect.types.info_base import CollectingInfoBase
from labridge.tools.base.tool_log import (
	ToolLog,
	TOOL_OP_DESCRIPTION,
	TOOL_REFERENCES,
)
from labridge.callback.base.operation_log import (
	OperationOutputLog,
	OP_REFERENCES,
	OP_DESCRIPTION,
)
from labridge.interact.collect.pipeline import (
	collect_info_from_user,
	acollect_info_from_user,
)

from abc import abstractmethod
from typing import (
	Callable,
	Any,
	List,
	Dict,
)


class CollectAndAuthorizeTool(CallBackBaseTool):
	r"""
	This tool is the template for tools whose process involves information collection from users
	and the getting final operation authorization from the user.

	Args:
		tool_fn (Callable): The function that executes the entire process of a specific tool.
		tool_async_fn (Callable): The function that asynchronously executes the entire process of a specific tool.
		callback_operation (CallBackOperationBase): The operation that needs the user's authorization.
		tool_name (str): The tool name, recommend the name of the specified tool class.
		llm (LLM): The used large language model.
		embed_model (BaseEmbedding): The used embedding model.
		verbose (bool): Whether to show the inner progress.
	"""
	def __init__(
		self,
		tool_fn: Callable[..., Any],
		tool_async_fn: Callable[..., Any],
		callback_operation: CallBackOperationBase,
		tool_name: str = None,
		llm: LLM = None,
		embed_model: BaseEmbedding = None,
		verbose: bool = False,
	):
		self._llm = llm or Settings.llm
		self._embed_model = embed_model or Settings.embed_model
		self._verbose = verbose
		super().__init__(
			fn=tool_fn,
			async_fn=tool_async_fn,
			tool_name=tool_name,
			callback_operation=callback_operation,
		)

	@abstractmethod
	def required_infos(self) -> List[CollectingInfoBase]:
		r""" The required infos. """


	@abstractmethod
	def required_info_dict(self) -> Dict[str, str]:
		r""" The required info names and their descriptions """

	def log(self, **kwargs: Any) -> ToolLog:
		r"""
		Record the tool's logs.

		Args:
			**kwargs: The input keyword arguments and the (output, log) of the callback operation.

		Returns:
			tool_log (ToolLog): The tool logs, including tool_to_user and tool_to_system.
		"""
		user_id = kwargs["user_id"]
		collected_info = ",".join(list(self.required_info_dict().keys()))
		log_to_system_str = (
			f"Have collected these information from the user {user_id}:\n"
			f"{collected_info}\n"
			f"Then try to do the following operation.\n"
		)

		op_log: OperationOutputLog = kwargs["operation_log"]
		if not isinstance(op_log, OperationOutputLog):
			raise ValueError("The operation_log must be 'OperationOutputLog'.")

		log_to_system_str += op_log.log_to_system[OP_DESCRIPTION]

		log_to_user = op_log.log_to_user
		log_to_system = {
			TOOL_OP_DESCRIPTION: log_to_system_str,
			TOOL_REFERENCES: op_log.log_to_system[OP_REFERENCES],
		}

		tool_log = ToolLog(
			tool_name=self.metadata.name,
			log_to_user=log_to_user,
			log_to_system=log_to_system,
			tool_abort=op_log.operation_abort,
		)
		return tool_log

	def collect_and_authorize(
		self,
		user_id: str,
		query_str: str,
	) -> FuncOutputWithLog:
		r"""
		This Method is a template method can be reused in subclass to reduce code redundancy.

		Firstly, this method will collect the required infos from the user.
		Then, the agent will generate the operation description according to the collected information.
		Finally, the agent will ask for the user's authorization to execute the operation.

		Args:
			user_id (str): The user_id of a lab member.
			query_str (str): The query from the user.

		Returns:
			output_log (FuncOutputWithLog):
				including the output of the callback operation and the tool's log.
		"""
		info_dict = collect_info_from_user(
			user_id=user_id,
			required_infos=self.required_infos(),
			query_str=query_str,
		)

		if info_dict is None:
			op_name = self._callback_operation.__name__
			operation_log_str = (
				f"The user {user_id} aborts this operation {op_name}."
			)
			operation_log = OperationOutputLog(
				operation_name=op_name,
				operation_output=None,
				log_to_user=None,
				log_to_system={
					OP_DESCRIPTION: operation_log_str,
					OP_REFERENCES: None,
				},
				operation_abort=True,
			)
			log_dict = {"operation_log": operation_log}

			return FuncOutputWithLog(
				fn_output=f"The user {user_id} abort the collecting process in the operation {op_name}",
				fn_log=log_dict,
			)

		op_name = self._callback_operation.__name__
		kwargs = {"user_id": user_id, }
		for key in self.required_info_dict().keys():
			kwargs[key] = info_dict[key]
		kwargs_str = json.dumps(kwargs)
		operation_log = operation_authorize(
			user_id=user_id,
			op_name=op_name,
			kwargs_str=kwargs_str,
			llm=self._llm,
			embed_model=self._embed_model,
			verbose=self._verbose,
		)
		log = {"operation_log": operation_log}
		fn_output = f"Have done the operation {op_name} with the agreement of the user {user_id}."
		if operation_log.operation_output is not None:
			fn_output += f"\nOperation output:\n{operation_log.operation_output}"
		return FuncOutputWithLog(
			fn_output=fn_output,
			fn_log=log,
		)

	async def acollect_and_authorize(
		self,
		user_id: str,
		query_str: str,
	) -> FuncOutputWithLog:
		r"""
		This Method is an asynchronous version template method can be reused in subclass to reduce code redundancy.

		Firstly, this method will collect the required infos from the user.
		Then, the agent will generate the operation description according to the collected information.
		Finally, the agent will ask for the user's authorization to execute the operation.

		Args:
			user_id (str): The user_id of a lab member.
			query_str (str): The query from the user.

		Returns:
			output_log (FuncOutputWithLog):
				including the output of the callback operation and the tool's log.
		"""
		info_dict = await acollect_info_from_user(
			user_id=user_id,
			required_infos=self.required_infos(),
			query_str=query_str,
		)

		op_name = self._callback_operation.__name__
		if info_dict is None:
			operation_log_str = (
				f"The user {user_id} abort this operation."
			)
			operation_log = OperationOutputLog(
				operation_name=self._callback_operation.__name__,
				operation_output=None,
				log_to_user=None,
				log_to_system={
					OP_DESCRIPTION: operation_log_str,
					OP_REFERENCES: None,
				},
				operation_abort=True,
			)
			log_dict = {"operation_log": operation_log}
			return FuncOutputWithLog(
				fn_output=f"The user {user_id} abort the collecting process in the operation {op_name}",
				fn_log=log_dict,
			)

		kwargs = {"user_id": user_id, }
		for key in self.required_info_dict().keys():
			kwargs[key] = info_dict[key]
		kwargs_str = json.dumps(kwargs)
		operation_log = await aoperation_authorize(
			user_id=user_id,
			op_name=op_name,
			kwargs_str=kwargs_str,
			llm=self._llm,
			embed_model=self._embed_model,
			verbose=self._verbose,
		)
		print("Here: after refuse: ", operation_log)
		log_dict = {"operation_log": operation_log}
		fn_output = f"Have done the operation {op_name} with the agreement of the user {user_id}."
		if operation_log.operation_output is not None:
			fn_output += f"\nOperation output:\n{operation_log.operation_output}"
		return FuncOutputWithLog(
			fn_output=fn_output,
			fn_log=log_dict,
		)