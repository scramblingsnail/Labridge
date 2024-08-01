from llama_index.core.tools.utils import create_schema_from_function
from llama_index.core.base.base_query_engine import BaseQueryEngine
from llama_index.core.bridge.pydantic import BaseModel
from llama_index.core.tools.types import AsyncBaseTool
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore
from llama_index.core.tools.types import (
	ToolMetadata,
	ToolOutput,
)
from llama_index.core.tools import (
	FunctionTool,
	QueryEngineTool,
)

from inspect import signature
from abc import abstractmethod
from typing import (
	Callable,
	Any,
	Optional,
	List,
	Type,
	Union,
)

from labridge.paper.query_engine.paper_query_engine import PAPER_QUERY_TOOL_NAME
from .utils import (
	pack_tool_output,
	create_schema_from_class_method,
)


r"""
All tool output will be followed by a log string that describe the tool's operation.
"""


# The tool_log of these tools will be recorded in the chat memory and sent to the user.
OUTPUT_LOG_TOOLS = [
	PAPER_QUERY_TOOL_NAME,
]

TOOL_LOG_TYPE = Union[str, List[str]]



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
		r""" Return the log json string, describing the tool's operation. """

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
	def log(self) -> str:
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

class RetrieverBaseTool(AsyncBaseTool):
	def __init__(
		self,
		name: str,
		retriever: BaseRetriever,
		retrieve_fn: Callable,
		description: Optional[str] = None,
	):
		fn_schema = self._get_retriever_fn_schema(name=name, fn=retrieve_fn)
		description = description or self._retriever_fn_description_from_docstring(name=name, fn=retrieve_fn)

		self._retriever = retriever
		self._metadata = ToolMetadata(
			name=name,
			description=description,
			fn_schema=fn_schema,
		)

	def _get_retriever_fn_schema(self, name: str, fn: Callable) -> Type[BaseModel]:
		fn_schema = create_schema_from_class_method(name=name, func=fn)
		return fn_schema

	def _retriever_fn_description_from_docstring(self, name: str, fn: Callable) -> str:
		docstring = fn.__doc__
		description = f"{name}{signature(fn)}\n{docstring}"
		return description

	@abstractmethod
	def log(self, retrieve_kwargs: dict) -> str:
		r""" Return the log string. """

	@abstractmethod
	def _get_retriever_input(self, *args: Any, **kwargs: Any) -> dict:
		r""" Parse the input of the call method to the input of the retrieve method of the retriever. """

	@abstractmethod
	def _retrieve(self, retrieve_kwargs: dict) -> List[NodeWithScore]:
		r""" Use the retriever to retrieve relevant nodes. """

	@abstractmethod
	async def _aretrieve(self, retrieve_kwargs: dict) -> List[NodeWithScore]:
		r""" Asynchronously use the retriever to retrieve relevant nodes. """

	@abstractmethod
	def _nodes_to_tool_output(self, nodes: List[NodeWithScore]) -> str:
		r""" output the retrieved contents in a specific format. """

	@property
	def retriever(self) -> BaseRetriever:
		return self._retriever

	@property
	def metadata(self) -> ToolMetadata:
		return self._metadata

	def call(self, *args: Any, **kwargs: Any) -> ToolOutput:
		retrieve_kwargs = self._get_retriever_input(*args, **kwargs)
		nodes = self._retrieve(retrieve_kwargs=retrieve_kwargs)
		retrieve_output = self._nodes_to_tool_output(nodes=nodes)
		tool_log = self.log(retrieve_kwargs)

		content = pack_tool_output(tool_output=retrieve_output, tool_log=tool_log)
		return ToolOutput(
			content=content,
			tool_name=self.metadata.name,
			raw_input={"input": retrieve_kwargs},
			raw_output=nodes,
		)

	async def acall(self, *args: Any, **kwargs: Any) -> ToolOutput:
		retrieve_kwargs = self._get_retriever_input(*args, **kwargs)
		nodes = await self._aretrieve(retrieve_kwargs=retrieve_kwargs)
		retrieve_output = self._nodes_to_tool_output(nodes=nodes)
		tool_log = self.log(retrieve_kwargs=retrieve_kwargs)

		content = pack_tool_output(tool_output=retrieve_output, tool_log=tool_log)
		return ToolOutput(
			content=content,
			tool_name=self.metadata.name,
			raw_input={"input": retrieve_kwargs},
			raw_output=nodes,
		)




