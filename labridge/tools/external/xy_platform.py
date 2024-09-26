import json

from llama_index.core.llms import LLM
from llama_index.core import Settings
from llama_index.core.embeddings import BaseEmbedding

from labridge.tools.base.function_base_tools import CallBackBaseTool, FuncOutputWithLog
from labridge.tools.base.tool_log import ToolLog, TOOL_OP_DESCRIPTION, TOOL_REFERENCES
from labridge.callback.base.operation_log import OperationOutputLog, OP_DESCRIPTION, OP_REFERENCES
from labridge.interact.authorize.authorize import operation_authorize, aoperation_authorize
from labridge.callback.external.xy_platform import XYPlatformOperation

from typing import Any


class XYPlatformMoveTool(CallBackBaseTool):
	r"""
	This tool is used to move a motorized XY stage, the motorized XY stage can be moved along the `X` axis and `Y` axis.

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
			fn=self.move,
			async_fn=self.amove,
			tool_name=XYPlatformMoveTool.__name__,
			callback_operation=XYPlatformOperation,
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

	def move(
		self,
		user_id: str,
		x_direction: int,
		x_movement: int,
		y_direction: int,
		y_movement: int,
	) -> FuncOutputWithLog:
		r"""
		This tool is used to move a motorized XY stage along the `X` axis and `Y` axis.

		Args:
			user_id: The user id of a Lab member.
			x_direction (int): An integer representing the moving direction in `x` axis. 0 means moving to left, 1 means moving to right.
			x_movement (int): The distance moved along `x` axis. unit: millimeter.
				If there is no need to move along `x` axis, use integer 0 as the input.
			y_direction (int): An integer representing the moving direction in `y` axis. 0 means moving down, 1 means moving up.
			y_movement (int): The distance moved along `y` axis. unit: millimeter.
				If there is no need to move along `y` axis, use integer 0 as the input.

		Returns:
			FuncOutputWithLog: The output and log.
		"""
		# This docstring is used as the tool description.
		op_name = self._callback_operation.__name__
		kwargs = {
			"x_direction": x_direction,
			"x_movement": x_movement,
			"y_direction": y_direction,
			"y_movement": y_movement,
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
			fn_output=f"Have successfully moved the motorized XY stage according to the instruct of the user {user_id}",
			fn_log=log_dict,
		)

	async def amove(
		self,
		user_id: str,
		x_direction: int,
		x_movement: int,
		y_direction: int,
		y_movement: int,
	) -> FuncOutputWithLog:
		r"""
		This tool is used to move a motorized XY stage along the `X` axis and `Y` axis.

		Args:
			user_id: The user id of a Lab member.
			x_direction (int): An integer representing the moving direction in `x` axis. 0 means moving to left, 1 means moving to right.
			x_movement (int): The distance moved along `x` axis. unit: millimeter.
				If there is no need to move along `x` axis, use integer 0 as the input.
			y_direction (int): An integer representing the moving direction in `y` axis. 0 means moving down, 1 means moving up.
			y_movement (int): The distance moved along `y` axis. unit: millimeter.
				If there is no need to move along `y` axis, use integer 0 as the input.

		Returns:
			FuncOutputWithLog: The output and log.
		"""
		# This docstring is used as the tool description.
		op_name = self._callback_operation.__name__
		kwargs = {
			"x_direction": x_direction,
			"x_movement": x_movement,
			"y_direction": y_direction,
			"y_movement": y_movement,
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
			fn_output=f"Have successfully moved the motorized XY stage according to the instruct of the user {user_id}",
			fn_log=log_dict,
		)
