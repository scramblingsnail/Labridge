from llama_index.core.tools.types import (
	ToolMetadata,
	ToolOutput,
)
from llama_index.core.tools.function_tool import sync_to_async

from inspect import signature
from abc import abstractmethod
from typing import (
	Callable,
	Optional,
)

from labridge.tools.base.tool_log import ToolLog
from labridge.callback.base.operation_base import CallBackOperationBase
from labridge.tools.utils import (
	pack_tool_output,
	create_schema_from_fn_or_method,
)
from .tool_base import CheckBaseTool

from typing import Dict, Any, Union


class FuncOutputWithLog:
	r"""
	This class is the output format of the function in a FunctionBaseTool.

	Args:
		fn_output (str): The output of the function.
		fn_log (Union[str, Dict[str, Any]]): The log of the function.
	"""
	def __init__(
		self,
		fn_output: Optional[str],
		fn_log: Union[str, Dict[str, Any]]
	):
		self.fn_output = fn_output
		self.fn_log = fn_log


class FunctionBaseTool(CheckBaseTool):
	r"""
	This tool is the base of function-type or method-type tools.

	Args:
		fn (Callable): The function or method that will be called by the agent.
		async_fn (Callable): The asynchronous version of `fn`.
		tool_name (str): The tool name. If not specified, the `fn.__name__` will be used as the tool name.
		return_direct (str): Whether to return the tool output directly in the Reasoning & Acting process.
			Refer to `ReactAgent` for details.
	"""
	def __init__(
		self,
		fn: Callable[..., Any],
		async_fn: Callable[..., Any] = None,
		tool_name: str = None,
		return_direct: bool = False,
	):
		name = tool_name or fn.__name__
		docstring = fn.__doc__
		description = f"{name}{signature(fn)}\n{docstring}"
		fn_schema = create_schema_from_fn_or_method(f"{name}", fn, additional_fields=None)
		metadata = ToolMetadata(
			name=name,
			description=description,
			fn_schema=fn_schema,
			return_direct=return_direct,
		)

		self._fn = fn
		if async_fn is not None:
			self._async_fn = async_fn
		else:
			self._async_fn = sync_to_async(self._fn)
		super().__init__(metadata=metadata)

	@abstractmethod
	def log(self, **kwargs: Any) -> ToolLog:
		r""" Return the log json string, describing the tool's operation. """

	def call(self, **kwargs: Any) -> ToolOutput:
		""" Call, return output and log. """
		checked_kwargs = self._get_input(**kwargs)
		output_with_log = self._fn(**checked_kwargs)

		if not isinstance(output_with_log, FuncOutputWithLog):
			raise ValueError("The function of a function tool must output 'FuncOutputWithLog'.")

		fn_output = output_with_log.fn_output
		fn_log = output_with_log.fn_log
		if not isinstance(fn_log, dict):
			fn_log = {"fn_log": fn_log}
		else:
			fn_log = fn_log

		checked_kwargs.update(fn_log)
		tool_log = self.log(**checked_kwargs)
		tool_output = pack_tool_output(tool_output=fn_output, tool_log=tool_log.dumps())

		return ToolOutput(
			content=str(tool_output),
			tool_name=self.metadata.name,
			raw_input={"kwargs": kwargs},
			raw_output=tool_output,
		)

	async def acall(self, **kwargs: Any) -> ToolOutput:
		""" Asynchronous Call. """
		checked_kwargs = self._get_input(**kwargs)
		output_with_log = await self._async_fn(**checked_kwargs)
		if not isinstance(output_with_log, FuncOutputWithLog):
			raise ValueError("The function of a function tool must output 'FuncOutputWithLog'.")

		fn_output = output_with_log.fn_output
		fn_log = output_with_log.fn_log
		if not isinstance(fn_log, dict):
			fn_log = {"fn_log": fn_log}
		else:
			fn_log = fn_log

		checked_kwargs.update(fn_log)
		tool_log = self.log(**checked_kwargs)
		tool_output = pack_tool_output(tool_output=fn_output, tool_log=tool_log.dumps())
		return ToolOutput(
			content=str(tool_output),
			tool_name=self.metadata.name,
			raw_input={"kwargs": kwargs},
			raw_output=tool_output,
		)


class CallBackBaseTool(FunctionBaseTool):
	r"""
	This is base of tools that will execute operations that need authorization.
	Refer to the `callback` module for details.

	Args:
		fn (Callable): The function or method that will be called by the agent.
		async_fn (Callable): The asynchronous version of `fn`.
		callback_operation (CallBackOperationBase): The operation that needs the user's authorization.
		tool_name (str): The tool name.
		return_direct (bool): Whether to return the tool output directly in Reasoning & Acting process.
	"""
	def __init__(
		self,
		fn: Callable[..., Any],
		async_fn: Callable[..., Any],
		callback_operation: CallBackOperationBase,
		tool_name: str = None,
		return_direct: bool = False,
	):
		self._callback_operation = callback_operation
		super().__init__(
			fn=fn,
			async_fn=async_fn,
			tool_name=tool_name,
			return_direct=return_direct,
		)

	@abstractmethod
	def log(self, **kwargs: Any) -> ToolLog:
		r""" Return the log json string, describing the tool's operation. """
