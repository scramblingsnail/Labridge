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


from typing import Dict, Any


class FuncOutputWithLog:
	def __init__(
		self,
		fn_output: str,
		fn_log: Dict[str, Any]
	):
		self.fn_output = fn_output
		self.fn_log = fn_log







