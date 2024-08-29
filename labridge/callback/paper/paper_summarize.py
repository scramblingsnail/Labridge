import fsspec

from llama_index.core.embeddings import BaseEmbedding
from llama_index.core import Settings
from llama_index.core.llms import LLM
from llama_index.core.schema import NodeWithScore, TextNode
from llama_index.core.response import Response

from labridge.callback.base.operation_base import CallBackOperationBase
from labridge.callback.base.operation_log import OperationOutputLog, OP_DESCRIPTION, OP_REFERENCES

from pathlib import Path
from typing import cast

from labridge.func_modules.paper.store.temporary_store import RecentPaperStore
from labridge.func_modules.reference.paper import PaperInfo
from labridge.func_modules.paper.synthesizer.summarize import PaperBatchSummarize


SUMMARIZE_DESCRIPTION_TMPL = (
	"为{user_id}总结以下文献, 总结文献可能要稍微花几分钟时间哦。\n"
	"{paper_file_path}"
)


class PaperSummarizeOperation(CallBackOperationBase):
	r"""
	This operation will summarize a paper.

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
		root = Path(__file__)

		for idx in range(4):
			root = root.parent

		self.root = root
		self._fs = fsspec.filesystem("file")
		embed_model = embed_model or Settings.embed_model
		llm = llm or Settings.llm
		self._summarizer = PaperBatchSummarize(llm=llm)
		super().__init__(
			llm=llm,
			embed_model=embed_model,
			verbose=verbose,
			op_name=op_name or PaperSummarizeOperation.__name__,
		)

	def operation_description(self, **kwargs) -> str:
		r"""
		Describe the operation.

		Args:
			user_id (str): the user id.
			paper_file_path (str): The file path of the paper.

		Returns:
			str: the operation description.
		"""
		user_id = kwargs.get("user_id", None)
		paper_file_path = kwargs.get("paper_file_path", None)

		if None in [user_id, paper_file_path]:
			raise ValueError("should provide valid user_id, paper_infos.")

		description = SUMMARIZE_DESCRIPTION_TMPL.format(user_id=user_id, paper_file_path=paper_file_path)
		return description

	def do_operation(
		self,
		user_id: str,
		paper_file_path: str,
	) -> OperationOutputLog:
		r"""
		Execute the operation to summarize a paper in a user's recent papers.

		Args:
			user_id (str): The user id of a lab member.
			paper_file_path (str): The file path of the paper.

		Returns:
			OperationOutputLog:
				The operation output and log.
		"""
		recent_paper_store = RecentPaperStore.from_user_id(
			user_id=user_id,
			embed_model=self._embed_model,
		)
		recent_paper_store.check_valid_paper(paper_file_path=paper_file_path)
		summary_node = recent_paper_store.get_summary_node(paper_file_path=paper_file_path)
		if summary_node is not None:
			return summary_node.text

		# TODO: Send to the user
		print("Assistant: 正在为您总结中，请稍候。")
		paper_nodes = recent_paper_store.get_paper_nodes(paper_file_path=paper_file_path)
		nodes_with_scores = [NodeWithScore(node=n) for n in paper_nodes]
		# get the summary for each doc_id
		summary_response = self._summarizer.synthesize(
			nodes=nodes_with_scores,
			query=""
		)
		summary_response = cast(Response, summary_response)
		summary_node = TextNode(text=summary_response.response)
		recent_paper_store.insert_summary_node(
			paper_file_path=paper_file_path,
			summary_node=summary_node,
		)
		recent_paper_store.persist()
		paper_info = PaperInfo(
			title=paper_file_path,
			possessor=user_id,
			file_path=paper_file_path,
		)
		op_log = f"Have summarized the paper {paper_file_path} for the user {user_id}."
		return OperationOutputLog(
			operation_name=self.op_name,
			operation_output=summary_node.text,
			log_to_user=None,
			log_to_system={
				OP_DESCRIPTION: op_log,
				OP_REFERENCES: [paper_info.dumps()]
			},
		)

	async def ado_operation(
		self,
		user_id: str,
		paper_file_path: str,
	) -> OperationOutputLog:
		r"""
		Asynchronously execute the operation to summarize a paper in a user's recent papers.

		Args:
			user_id (str): The user id of a lab member.
			paper_file_path (str): The file path of the paper.

		Returns:
			OperationOutputLog:
				The output and log.
		"""
		recent_paper_store = RecentPaperStore.from_user_id(
			user_id=user_id,
			embed_model=self._embed_model,
		)
		recent_paper_store.check_valid_paper(paper_file_path=paper_file_path)
		summary_node = recent_paper_store.get_summary_node(paper_file_path=paper_file_path)
		if summary_node is not None:
			return summary_node.text

		# TODO: Send to the user
		print("Assistant: 正在为您总结中，请稍候。")
		paper_nodes = recent_paper_store.get_paper_nodes(paper_file_path=paper_file_path)
		nodes_with_scores = [NodeWithScore(node=n) for n in paper_nodes]
		# get the summary for each doc_id
		summary_response = await self._summarizer.asynthesize(
			nodes=nodes_with_scores,
			query=""
		)
		summary_response = cast(Response, summary_response)
		summary_node = TextNode(text=summary_response.response)
		recent_paper_store.insert_summary_node(
			paper_file_path=paper_file_path,
			summary_node=summary_node,
		)
		recent_paper_store.persist()
		paper_info = PaperInfo(
			title=paper_file_path,
			possessor=user_id,
			file_path=paper_file_path,
		)
		op_log = f"Have summarized the paper {paper_file_path} for the user {user_id}."
		return OperationOutputLog(
			operation_name=self.op_name,
			operation_output=summary_node.text,
			log_to_user=None,
			log_to_system={
				OP_DESCRIPTION: op_log,
				OP_REFERENCES: [paper_info.dumps()]
			},
		)
