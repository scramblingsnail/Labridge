from llama_index.core.embeddings import BaseEmbedding
from llama_index.core import Settings
from llama_index.core.llms import LLM
from labridge.tools.callback.base import CallBackOperationBase
from labridge.paper.store.temorary_store import RecentPaperStore



ADD_NEW_RECENT_PAPER_TMPL = (
"""
将把如下文献加入到 {user_id} 的临时文献库中：
{paper_file_path}
"""
)


class AddNewRecentPaperOperation(CallBackOperationBase):
	def __init__(
		self,
		llm: LLM = None,
		embed_model: BaseEmbedding = None,
		verbose: bool = False
	):
		embed_model = embed_model or Settings.embed_model
		llm = llm or Settings.llm
		super().__init__(
			embed_model=embed_model,
			llm=llm,
			verbose=verbose,
		)

	def operation_description(self, **kwargs) -> str:
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
	) -> str:
		r""" This method will execute the operation when authorized. And return the operation log """
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

		except Exception as e:
			op_log = f"Error: {e}"
		return op_log

	async def ado_operation(
		self,
		**kwargs
	) -> str:
		return self.do_operation(**kwargs)
