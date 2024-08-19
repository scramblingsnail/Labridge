import json
from llama_index.core.llms import LLM
from llama_index.core import Settings
from llama_index.core.embeddings import BaseEmbedding

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
from llama_index.core.tools.function_tool import sync_to_async
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
	Tuple,
	Dict,
)

from labridge.tools.base.tool_log import ToolLog, TOOL_OP_DESCRIPTION, TOOL_REFERENCES
from labridge.paper.query_engine.paper_query_engine import PAPER_QUERY_TOOL_NAME
from labridge.interact.authorize.authorize import operation_authorize, aoperation_authorize
from labridge.callback.base.operation_base import CallBackOperationBase
from labridge.interact.collect.pipeline import (
	collect_info_from_user,
	acollect_info_from_user,
)

from labridge.interact.collect.types.common_info import CollectingCommonInfo
from labridge.interact.collect.types.select_info import CollectingSelectInfo
from labridge.interact.collect.types.info_base import CollectingInfoBase

from labridge.tools.utils import (
	pack_tool_output,
	create_schema_from_fn_or_method,
)


r"""
All tool output will be followed by a log string that describe the tool's operation.
"""


# The tool_log of these tools will be recorded in the chat memory and sent to the user.
OUTPUT_LOG_TOOLS = [
	PAPER_QUERY_TOOL_NAME,
]

TOOL_LOG_TYPE = Union[str, List[str]]


class CheckBaseTool(AsyncBaseTool):
	r"""
	The base tool that will check the input keyword arguments according to the tool's fn_schema.

	Args:
		metadata (ToolMetadata): the tool's metadata.
	"""

	def __init__(self, metadata: ToolMetadata):
		self._metadata = metadata
		super().__init__()

	@property
	def metadata(self) -> ToolMetadata:
		return self._metadata

	def _get_input(self, **kwargs: Any) -> dict:
		r""" Parse the required keyword arguments from the provided keyword arguments. """
		fn_schema = json.loads(self.metadata.fn_schema_str)
		argument_keys = list(fn_schema["properties"].keys())
		required_kwargs = fn_schema["required"]
		missing_keys = []
		for key in required_kwargs:
			if key not in kwargs:
				missing_keys.append(key)
		if len(missing_keys) > 0:
			missing_keys = ','.join(missing_keys)
			raise ValueError(f"The required parameters are not provided: {missing_keys}")

		if "kwargs" in argument_keys:
			return kwargs

		return {key: kwargs[key] for key in argument_keys}

	@abstractmethod
	def call(self, **kwargs) -> ToolOutput:
		r""" Tool call """

	@abstractmethod
	async def acall(self, **kwargs) -> ToolOutput:
		r""" Asynchronously tool call """


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
	def log(self) -> ToolLog:
		r""" Return the ToolLog, describing the tool's operation. """

	def call(self, *args: Any, **kwargs: Any) -> ToolOutput:
		query_str = self._get_query_str(*args, **kwargs)
		response = self._query_engine.query(query_str)
		tool_log = self.log()
		response = pack_tool_output(tool_output=str(response), tool_log=tool_log.dumps())
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
		response = pack_tool_output(tool_output=str(response), tool_log=tool_log.dumps())
		return ToolOutput(
			content=response,
			tool_name=self.metadata.name,
			raw_input={"input": query_str},
			raw_output=response,
		)

class RetrieverBaseTool(CheckBaseTool):
	r"""
	This is the base of retrieving tools.

	Args:
		name (str): The tool name.
		retriever (Any): The retriever that retrieves in something.
		retrieve_fn (Callable): The retrieving function or method that will be called by the agent.
		description (Optional[str]): The tool description. If not specified, the tool description will be set as the
			docstring of the `retrieve_fn`.
	"""
	def __init__(
		self,
		name: str,
		retriever: Any,
		retrieve_fn: Callable,
		description: Optional[str] = None,
	):
		fn_schema = self._get_retriever_fn_schema(name=name, fn=retrieve_fn)
		description = description or self._retriever_fn_description_from_docstring(name=name, fn=retrieve_fn)

		self._retriever = retriever
		metadata = ToolMetadata(
			name=name,
			description=description,
			fn_schema=fn_schema,
		)
		super().__init__(metadata=metadata)

	def _get_retriever_fn_schema(self, name: str, fn: Callable) -> Type[BaseModel]:
		r""" Get the fn_schema from the provided function or method. """
		fn_schema = create_schema_from_fn_or_method(name=name, func=fn)
		return fn_schema

	def _retriever_fn_description_from_docstring(self, name: str, fn: Callable) -> str:
		r""" Get the tool description from docstring of the function. """
		docstring = fn.__doc__
		description = f"{name}{signature(fn)}\n{docstring}"
		return description

	@abstractmethod
	def log(self, log_dict: dict) -> ToolLog:
		r""" Return the ToolLog with log string in a specific format. """

	@abstractmethod
	def _retrieve(self, retrieve_kwargs: dict) -> List[NodeWithScore]:
		r""" Use the retriever to retrieve relevant nodes. """

	@abstractmethod
	async def _aretrieve(self, retrieve_kwargs: dict) -> List[NodeWithScore]:
		r""" Asynchronously use the retriever to retrieve relevant nodes. """

	@abstractmethod
	def _nodes_to_tool_output(self, nodes: List[NodeWithScore]) -> Tuple[str, dict]:
		r""" output the retrieved contents in a specific format, and the output log. """

	@property
	def retriever(self) -> BaseRetriever:
		return self._retriever

	@property
	def metadata(self) -> ToolMetadata:
		return self._metadata

	def call(self, **kwargs: Any) -> ToolOutput:
		r"""
		Call the retrieving function or method, and pack the output and logs.

		Args:
			**kwargs: The keyword arguments will be provided by the agent.

		Returns:
			ToolOutput: The tool output and logs.

		"""
		retrieve_kwargs = self._get_input(**kwargs)
		nodes = self._retrieve(retrieve_kwargs=retrieve_kwargs)
		retrieve_output, output_log_dict = self._nodes_to_tool_output(nodes=nodes)
		output_log_dict.update(retrieve_kwargs)
		tool_log = self.log(log_dict=output_log_dict)

		content = pack_tool_output(tool_output=retrieve_output, tool_log=tool_log.dumps())
		return ToolOutput(
			content=content,
			tool_name=self.metadata.name,
			raw_input={"input": retrieve_kwargs},
			raw_output=nodes,
		)

	async def acall(self, **kwargs: Any) -> ToolOutput:
		r"""
		Asynchronously call the retrieving function or method, and pack the output and logs.

		Args:
			**kwargs: The keyword arguments will be provided by the agent.

		Returns:
			ToolOutput: The tool output and logs.

		"""
		retrieve_kwargs = self._get_input(**kwargs)
		nodes = await self._aretrieve(retrieve_kwargs=retrieve_kwargs)
		retrieve_output, output_log_dict = self._nodes_to_tool_output(nodes=nodes)
		output_log_dict.update(retrieve_kwargs)
		tool_log = self.log(log_dict=output_log_dict)

		content = pack_tool_output(tool_output=retrieve_output, tool_log=tool_log.dumps())
		return ToolOutput(
			content=content,
			tool_name=self.metadata.name,
			raw_input={"input": retrieve_kwargs},
			raw_output=nodes,
		)
