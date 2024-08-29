from abc import abstractmethod
from llama_index.core.llms import LLM
from llama_index.core.embeddings import BaseEmbedding

from .operation_log import OperationOutputLog


class CallBackOperationBase(object):
	r"""
	This is base class for callback operation.
	Here, callback operations indicate those operations requiring the user's permission.

	Args:
		llm (LLM): The used LLM.
		embed_model (BaseEmbedding): The used embedding model.
		verbose (bool): Whether to show the inner progress.
	"""
	def __init__(
		self,
		llm: LLM,
		embed_model: BaseEmbedding,
		op_name: str,
		verbose: bool = False,
	):
		self.op_name = op_name
		self._llm = llm
		self._embed_model = embed_model
		self._verbose = verbose


	@abstractmethod
	def operation_description(self, **kwargs) -> str:
		r""" This method return the description of the operation, which is presented to the users. """

	@abstractmethod
	def do_operation(self, **kwargs) -> OperationOutputLog:
		r""" This method will execute the operation when authorized. And return the operation log """

	@abstractmethod
	async def ado_operation(self, **kwargs) -> OperationOutputLog:
		r""" This method will asynchronously execute the operation when authorized. And return the operation log """
