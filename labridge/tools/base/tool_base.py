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
from labridge.tools.interact.autorize import operation_authorize, aoperation_authorize
from labridge.tools.callback.base import CallBackOperationBase
from labridge.tools.interact.collect_info import (
	collect_info_from_user,
	acollect_info_from_user,
)
from .utils import (
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

	def __init__(self, metadata: ToolMetadata):
		self._metadata = metadata
		super().__init__()

	@property
	def metadata(self) -> ToolMetadata:
		return self._metadata

	def _get_input(self, **kwargs: Any) -> dict:
		r""" Parse the input of the call method to the input of the function. """
		fn_schema = json.loads(self.metadata.fn_schema_str)
		argument_keys = list(fn_schema["properties"].keys())
		required_kwargs = fn_schema["required"]
		missing_keys = []
		for key in required_kwargs:
			if key not in kwargs:
				missing_keys.append(key)
		if len(missing_keys) > 0:
			raise ValueError(f"The required parameters are not provided: {','.join(missing_keys)}")

		if "kwargs" in argument_keys:
			return kwargs

		return {key: kwargs[key] for key in argument_keys}

	@abstractmethod
	def call(self, **kwargs) -> ToolOutput:
		r""" Tool call """

	@abstractmethod
	async def acall(self, **kwargs) -> ToolOutput:
		r""" Asynchronously tool call """




class FunctionBaseTool(CheckBaseTool):
	def __init__(
		self,
		fn: Callable[..., Any],
		async_fn: Callable[..., Any] = None,
		tool_name: str = None,
		return_direct: bool = False,
	):
		name = tool_name or fn.__name__
		docstring = fn.__doc__
		description = f"{fn.__name__}{signature(fn)}\n{docstring}"
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
		"""Call. and add log suffix"""
		checked_kwargs = self._get_input()
		fn_output = self._fn(**checked_kwargs)
		if not isinstance(fn_output, dict):
			fn_log = {"fn_log": fn_output}
		else:
			fn_log = fn_output

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
		"""Call."""
		checked_kwargs = self._get_input()
		fn_output = await self._async_fn(**checked_kwargs)
		if not isinstance(fn_output, dict):
			fn_log = {"fn_log": fn_output}
		else:
			fn_log = fn_output

		checked_kwargs.update(fn_log)
		tool_log = self.log(**checked_kwargs)
		tool_output = pack_tool_output(tool_output=fn_output, tool_log=tool_log.dumps())
		return ToolOutput(
			content=str(tool_output),
			tool_name=self.metadata.name,
			raw_input={"kwargs": kwargs},
			raw_output=tool_output,
		)


class CollectAndAuthorizeTool(FunctionBaseTool):
	r"""
	TODO: Docstring.

	"""
	def __init__(
		self,
		tool_fn: Callable[..., Any],
		tool_async_fn: Callable[..., Any],
		required_infos: Dict[str, str],
		callback_operation: CallBackOperationBase,
		tool_name: str = None,
		llm: LLM = None,
		embed_model: BaseEmbedding = None,
		verbose: bool = False,
	):
		self._required_infos = required_infos
		self._callback_operation = callback_operation
		self._llm = llm or Settings.llm
		self._embed_model = embed_model or Settings.embed_model
		self._verbose = verbose
		super().__init__(
			fn=tool_fn,
			async_fn=tool_async_fn,
			tool_name=tool_name,
		)

	def log(self, **kwargs: Any) -> ToolLog:
		op_log = (
			"Have collected these information from the user"
		)

		op_log = kwargs["operation_log"]
		return json.dumps([op_log])

	def collect_and_authorize(self, user_id: str, query_str: str) -> Dict[str, str]:
		info_dict = collect_info_from_user(
			user_id=user_id,
			required_infos=self._required_infos,
			query_str=query_str,
		)

		if info_dict is None:
			operation_log_str = (
				f"The user {user_id} aborts this operation."
			)
			operation_log = {"operation_log": operation_log_str}
			return operation_log

		op_name = self._callback_operation.__name__
		kwargs = {"user_id": user_id, }
		for key in self._required_infos.keys():
			kwargs[key] = info_dict[key]
		kwargs_str = json.dumps(kwargs)
		operation_log_str = operation_authorize(
			user_id=user_id,
			op_name=op_name,
			kwargs_str=kwargs_str,
			llm=self._llm,
			embed_model=self._embed_model,
			verbose=self._verbose,
		)
		operation_log = {"operation_log": operation_log_str}
		return operation_log

	async def acollect_and_authorize(self, user_id: str, query_str: str) -> Dict[str, str]:
		info_dict = await acollect_info_from_user(
			user_id=user_id,
			required_infos=self._required_infos,
			query_str=query_str,
		)

		if info_dict is None:
			operation_log_str = (
				f"The user {user_id} abort this operation."
			)
			operation_log = {"operation_log": operation_log_str}
			return operation_log

		op_name = self._callback_operation.__name__
		kwargs = {"user_id": user_id, }
		for key in self._required_infos.keys():
			kwargs[key] = info_dict[key]
		kwargs_str = json.dumps(kwargs)
		operation_log_str = await aoperation_authorize(
			user_id=user_id,
			op_name=op_name,
			kwargs_str=kwargs_str,
			llm=self._llm,
			embed_model=self._embed_model,
			verbose=self._verbose,
		)
		operation_log = {"operation_log": operation_log_str}
		return operation_log


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

class RetrieverBaseTool(CheckBaseTool):
	r"""

	retrieve_fn: used to collect fn_schema and fn_description.
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
		fn_schema = create_schema_from_fn_or_method(name=name, func=fn)
		return fn_schema

	def _retriever_fn_description_from_docstring(self, name: str, fn: Callable) -> str:
		docstring = fn.__doc__
		description = f"{name}{signature(fn)}\n{docstring}"
		return description

	@abstractmethod
	def log(self, log_dict: dict) -> str:
		r""" Return the log string in a specific format. """

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
		retrieve_kwargs = self._get_input(**kwargs)
		nodes = self._retrieve(retrieve_kwargs=retrieve_kwargs)
		retrieve_output, output_log_dict = self._nodes_to_tool_output(nodes=nodes)
		output_log_dict.update(retrieve_kwargs)
		tool_log = self.log(log_dict=output_log_dict)

		content = pack_tool_output(tool_output=retrieve_output, tool_log=tool_log)
		return ToolOutput(
			content=content,
			tool_name=self.metadata.name,
			raw_input={"input": retrieve_kwargs},
			raw_output=nodes,
		)

	async def acall(self, **kwargs: Any) -> ToolOutput:
		retrieve_kwargs = self._get_input(**kwargs)
		nodes = await self._aretrieve(retrieve_kwargs=retrieve_kwargs)
		retrieve_output, output_log_dict = self._nodes_to_tool_output(nodes=nodes)
		output_log_dict.update(retrieve_kwargs)
		tool_log = self.log(log_dict=output_log_dict)

		content = pack_tool_output(tool_output=retrieve_output, tool_log=tool_log)
		return ToolOutput(
			content=content,
			tool_name=self.metadata.name,
			raw_input={"input": retrieve_kwargs},
			raw_output=nodes,
		)
