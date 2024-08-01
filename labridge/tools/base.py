from llama_index.core.tools import FunctionTool, QueryEngineTool
from llama_index.core.base.base_query_engine import BaseQueryEngine
from typing import Callable, Any, Optional
from inspect import signature
from llama_index.core.tools.utils import create_schema_from_function
from llama_index.core.tools.types import ToolMetadata, ToolOutput
from abc import abstractmethod

from .utils import pack_tool_output

r"""
All tool output will be followed by a log string that describe the tool's operation.
"""


class FunctionBaseTool(FunctionTool):
	def __init__(
		self,
		fn: Callable[..., Any],
		return_direct: bool = False,
	):
		name = fn.__name__
		docstring = fn.__doc__
		description = f"{name}{signature(fn)}\n{docstring}"
		fn_schema = create_schema_from_function(f"{name}", fn, additional_fields=None)
		tool_metadata = ToolMetadata(
			name=name,
			description=description,
			fn_schema=fn_schema,
			return_direct=return_direct,
		)
		super().__init__(fn=fn, metadata=tool_metadata)

	@abstractmethod
	def log(self, *args: Any, **kwargs: Any) -> str:
		r""" Return the log string, describing the tool's operation. """

	def call(self, *args: Any, **kwargs: Any) -> ToolOutput:
		"""Call. and add log suffix"""
		tool_output = self._fn(*args, **kwargs)
		tool_log = self.log()
		tool_output = pack_tool_output(tool_output=tool_output, tool_log=tool_log)
		return ToolOutput(content=str(tool_output), tool_name=self.metadata.name,
			raw_input={"args": args, "kwargs": kwargs}, raw_output=tool_output, )

	async def acall(self, *args: Any, **kwargs: Any) -> ToolOutput:
		"""Call."""
		tool_output = await self._async_fn(*args, **kwargs)
		tool_log = self.log()
		tool_output = pack_tool_output(tool_output=tool_output, tool_log=tool_log)
		return ToolOutput(content=str(tool_output), tool_name=self.metadata.name,
			raw_input={"args": args, "kwargs": kwargs}, raw_output=tool_output, )


class QueryEngineBaseTool(QueryEngineTool):
	def __init__(
		self,
		query_engine: BaseQueryEngine,
		name: str,
		description: str,
		return_direct: bool = False,
		resolve_input_errors: bool = True,
	):
		metadata = ToolMetadata(name=name, description=description, return_direct=return_direct)
		super().__init__(
			query_engine=query_engine,
			metadata=metadata,
			resolve_input_errors=resolve_input_errors,
		)

	@abstractmethod
	def log(self) -> Optional[str]:
		r""" Return the log string, describing the tool's operation. """

	def call(self, *args: Any, **kwargs: Any) -> ToolOutput:
		query_str = self._get_query_str(*args, **kwargs)
		response = self._query_engine.query(query_str)
		tool_log = self.log()
		response = pack_tool_output(tool_output=str(response), tool_log=tool_log)
		return ToolOutput(
			content=response,
			tool_name=self.metadata.name,
			raw_input={"input": query_str},
			raw_output=response,
		)

	async def acall(self, *args: Any, **kwargs: Any) -> ToolOutput:
		query_str = self._get_query_str(*args, **kwargs)
		response = await self._query_engine.aquery(query_str)
		tool_log = self.log()
		response = pack_tool_output(tool_output=str(response), tool_log=tool_log)
		return ToolOutput(
			content=response,
			tool_name=self.metadata.name,
			raw_input={"input": query_str},
			raw_output=response,
		)
