from llama_index.core.embeddings import BaseEmbedding
from llama_index.core import Settings
from llama_index.core.llms import LLM
from labridge.callback.base.operation_base import CallBackOperationBase
from labridge.callback.base.operation_log import OperationOutputLog, OP_DESCRIPTION, OP_REFERENCES
from labridge.func_modules.paper.store.temporary_store import RecentPaperStore
from labridge.func_modules.reference.paper import PaperInfo


ADD_NEW_RECENT_PAPER_TMPL = (
"""
将把如下文献加入到 {user_id} 的临时文献库中：
{paper_file_path}
"""
)


class AddNewRecentPaperOperation(CallBackOperationBase):
	r"""
	This operation will add a new paper into a user's recent papers.

	Args:
		llm (LLM): The used LLM.
		embed_model (BaseEmbedding): The used embedding model.
		verbose (bool): Whether to show the inner progress.
	"""
	def __init__(
		self,
		llm: LLM = None,
		embed_model: BaseEmbedding = None,
		verbose: bool = False,
		op_name: str = None,
	):
		embed_model = embed_model or Settings.embed_model
		llm = llm or Settings.llm
		super().__init__(
			embed_model=embed_model,
			llm=llm,
			verbose=verbose,
			op_name=op_name or AddNewRecentPaperOperation.__name__,
		)

	def operation_description(self, **kwargs) -> str:
		r"""
		Return the operation description, this description will be sent to the user for authorization.

		Args:
			user_id (str): The user id of a lab member.
			paper_file_path (str): The file path of the new paper.

		Returns:
			str: The operation description.
		"""
		user_id = kwargs.get("user_id", None)
		paper_file_path = kwargs.get("paper_file_path", None)

		if None in [user_id, paper_file_path]:
			raise ValueError(f"Should provide these arguments: user_id, paper_file_path.")
		return ADD_NEW_RECENT_PAPER_TMPL.format(
			user_id=user_id,
			paper_file_path=paper_file_path,
		)

	def do_operation(
		self,
		**kwargs
	) -> OperationOutputLog:
		r"""
		Execute the operation after authorized to add a new paper to a user's recent papers.

		Args:
			user_id (str): The user id of a lab member.
			paper_file_path (str): The file path of the new paper.

		Returns:
			OperationOutputLog: The output and log of the operation.
		"""
		user_id = kwargs.get("user_id", None)
		paper_file_path = kwargs.get("paper_file_path", None)

		if None in [user_id, paper_file_path]:
			raise ValueError(f"Should provide these arguments: user_id, paper_file_path.")

		paper_store = RecentPaperStore.from_user_id(
			user_id=user_id,
			embed_model=self._embed_model,
		)
		try:
			paper_store.put(paper_file_path=paper_file_path)
			paper_store.persist()
			op_log = (
				f"Have put a new paper to the recent papers of the user {user_id}\n"
				f"Paper file path: {paper_file_path}"
			)
			paper_info = PaperInfo(
				file_path=paper_file_path,
				possessor=user_id,
				title=paper_file_path,
			)
			return OperationOutputLog(
				operation_name=self.op_name,
				operation_output=None,
				log_to_user=None,
				log_to_system={
					OP_DESCRIPTION: op_log,
					OP_REFERENCES: [paper_info.dumps()]
				}
			)

		except Exception as e:
			op_log = f"Error: {e}"
			return OperationOutputLog(
				operation_name=self.op_name,
				operation_output=None,
				log_to_user=None,
				log_to_system={
					OP_DESCRIPTION: op_log,
					OP_REFERENCES: None
				}
		)

	async def ado_operation(
		self,
		**kwargs
	) -> OperationOutputLog:
		return self.do_operation(**kwargs)
