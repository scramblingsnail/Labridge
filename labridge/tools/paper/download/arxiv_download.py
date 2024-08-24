import json

from arxiv import Result
from typing import List, Dict, Tuple
from llama_index.core.llms import LLM
from llama_index.core import Settings
from llama_index.core.utils import print_text
from llama_index.core.embeddings import BaseEmbedding

from labridge.interact.authorize.authorize import operation_authorize, aoperation_authorize
from labridge.accounts.users import AccountManager
from labridge.callback.base.operation_log import OperationOutputLog, OP_DESCRIPTION, OP_REFERENCES
from labridge.tools.base.tool_log import ToolLog, TOOL_OP_DESCRIPTION, TOOL_REFERENCES
from labridge.paper.download.arxiv import ArxivSearcher
from labridge.callback.paper.paper_download import ArxivDownloadOperation
from labridge.tools.base.function_base_tools import CallBackBaseTool, FuncOutputWithLog
from labridge.interface.server_backend import SocketManager, ClientSocketType

MAX_SEARCH_RESULTS_NUM = 5


USER_SELECT_ARXIV_PAPERS_QUERY = \
"""
为您在 arXiv 检索到如下文献，请告诉我您感兴趣的文献序号（数字）哦。
"""

ARXIV_PAPER_INFO_TMPL = \
"""
**文献 {paper_idx}**:
标题: {title}
摘要: 
	{abstract}
"""


def search_arxiv(search_str: str, max_results_num: int = 3) -> List[Result]:
	r"""
	Search in aXiv.org

	Args:
		search_str (str): the search string.
		max_results_num (int): the maximum number of returned results. Defaults to 3.

	Returns:
		the paper info results.
	"""
	searcher = ArxivSearcher(max_results_num=max_results_num)
	results = searcher.search(search_str)
	if len(results) < 1:
		raise ValueError("Do not find relevant papers.")

	return results


class ArXivSearchDownloadTool(CallBackBaseTool):
	r"""
	This tool is used to search and download papers from arXiv.org for the user.

	Args:
		llm (LLM): The used LLM.
		embed_model (BaseEmbedding): The used embedding model.
		verbose (bool): Whether to show the inner progress.
		max_results_num (int): The maximum search results that are presented to the user.
			The actually used value is `min(max_results_num, MAX_SEARCH_RESULTS_NUM)`.
	"""
	def __init__(
		self,
		llm: LLM = None,
		embed_model: BaseEmbedding = None,
		verbose: bool = False,
		max_results_num: int = 3,
	):
		self._llm = llm or Settings.llm
		self._embed_model = embed_model or Settings.embed_model
		self._verbose = verbose
		self._max_results_num = min(max_results_num, MAX_SEARCH_RESULTS_NUM)
		super().__init__(
			fn=self.search_download_pipeline,
			async_fn=self.asearch_download_pipeline,
			tool_name=ArXivSearchDownloadTool.__name__,
			callback_operation=ArxivDownloadOperation,
		)
		self.account_manager = AccountManager()

	def _user_select_results(self, user_id: str, results: List[Result]) -> Tuple[List[int], str]:
		r""" Let the user select among the candidate papers """
		query_str = self._select_query(results=results)
		# TODO: Send the query str to the user.
		to_user_msg = f"Assistant:\nDear{user_id},{query_str}"
		print(to_user_msg)

		# TODO receive the message from the user.
		user_response = input("User: ")

		numbers = self._parse_user_select(
			user_response=user_response,
			result_num=len(results),
		)
		indices = [n - 1 for n in numbers]
		return indices, user_response

	async def _auser_select_results(self, user_id: str, results: List[Result]) -> Tuple[List[int], str]:
		r""" Let the user select among the candidate papers """
		query_str = self._select_query(results=results)
		# TODO: Send the query str to the user.
		to_user_msg = f"Assistant:\nDear{user_id},{query_str}"
		await SocketManager.send_text_to_client(user_id=user_id, text=to_user_msg)

		# TODO receive the message from the user.
		user_response = await SocketManager.receive_text_from_client(user_id=user_id)

		numbers = self._parse_user_select(
			user_response=user_response,
			result_num=len(results),
		)
		indices = [n - 1 for n in numbers]
		return indices, user_response

	@staticmethod
	def _parse_user_select(user_response: str, result_num: int) -> List[int]:
		r""" parse the user response to select numbers """
		numbers = []
		digit_stack = []
		for char in user_response:
			if char.isdigit():
				digit_stack.append(char)
			else:
				if digit_stack:
					number = int("".join(digit_stack))
					if 0 < number <= result_num:
						numbers.append(int(number))
					digit_stack = []
		else:
			if digit_stack:
				number = int("".join(digit_stack))
				if 0 < number <= result_num:
					numbers.append(int(number))
		return numbers

	@staticmethod
	def _select_query(results: List[Result]) -> str:
		r""" The message including the searched paper infos. """
		query_str = USER_SELECT_ARXIV_PAPERS_QUERY
		papers = []
		for idx, result in enumerate(results):
			paper_info = ARXIV_PAPER_INFO_TMPL.format(
				paper_idx=idx + 1,
				title=result.title,
				abstract=result.summary,
			)
			papers.append(paper_info)
		query_str += "\n\n".join(papers)
		return query_str

	def log(self, *args, **kwargs) -> ToolLog:
		op_log: OperationOutputLog = kwargs["operation_log"]

		if not isinstance(op_log, OperationOutputLog):
			raise ValueError("operation_log must be 'OperationLog'.")

		log_to_user = op_log.log_to_user
		log_to_system = {
			TOOL_OP_DESCRIPTION: op_log.log_to_system[OP_DESCRIPTION],
			TOOL_REFERENCES: op_log.log_to_system[OP_REFERENCES],
		}

		return ToolLog(
			tool_name=self.metadata.name,
			log_to_system=log_to_system,
			log_to_user=log_to_user,
		)

	def search_download_pipeline(
		self,
		user_id: str,
		search_str: str,
		**kwargs,
	) -> FuncOutputWithLog:
		r"""
		This tool is used to search relevant papers in arXiv and download the papers that the user is interested in.
		When using the tool, be sure that the search_str MUST be English.
		If the user do not use English, translate the search string to English first.

		Args:
			user_id (str): The user_id of a lab member.
			search_str (str): The string that is used to search in arXiv.

		Returns:
			FuncOutputWithLog: the operation output and log.
		"""
		self.account_manager.check_valid_user(user_id=user_id)

		results = search_arxiv(search_str=search_str, max_results_num=self._max_results_num)
		indices, user_response = self._user_select_results(user_id=user_id, results=results)

		if len(indices) < 1:
			operation_log_str = (
				f"The user has no interest to the searched papers, end download operation.\n"
				f"This is the user's response: {user_response}"
			)
			operation_log = OperationOutputLog(
				operation_name=self._callback_operation.__name__,
				operation_output=None,
				log_to_user=None,
				log_to_system={
					OP_DESCRIPTION: operation_log_str,
					OP_REFERENCES: None,
				}
			)
			log_dict = {"operation_log": operation_log}
			return FuncOutputWithLog(
				fn_output=operation_log_str,
				fn_log=log_dict,
			)

		paper_infos = list()
		for idx in indices:
			paper = results[idx]
			paper_infos.append(
				{
					"title": paper.title,
					"abstract": paper.summary,
					"pdf_url": paper.pdf_url,
				}
			)

		op_name = ArxivDownloadOperation.__name__
		kwargs = {
			"user_id": user_id,
			"paper_infos": paper_infos
		}
		kwargs_str = json.dumps(kwargs)
		operation_log = operation_authorize(
			user_id=user_id,
			op_name=op_name,
			kwargs_str=kwargs_str,
			llm=self._llm,
			embed_model=self._embed_model,
			verbose=self._verbose,
		)
		log_dict = {"operation_log": operation_log}
		return FuncOutputWithLog(
			fn_output=f"Have downloaded papers for user {user_id}",
			fn_log=log_dict,
		)

	async def asearch_download_pipeline(
		self,
		user_id: str,
		search_str: str,
		**kwargs,
	) -> FuncOutputWithLog:
		r"""
		This tool is used to search relevant papers in arXiv and download the papers that the user is interested in.

		Args:
			user_id (str): The user_id of a lab member.
			search_str (str): The search string.

		Returns:
			FuncOutputWithLog: the operation output and log.
		"""
		self.account_manager.check_valid_user(user_id=user_id)

		results = search_arxiv(search_str=search_str, max_results_num=self._max_results_num)
		indices, user_response = await self._auser_select_results(user_id=user_id, results=results)

		if len(indices) < 1:
			operation_log_str = (
				f"The user has no interest to the searched papers, end download operation.\n"
				f"This is the user's response: {user_response}"
			)
			operation_log = OperationOutputLog(
				operation_name=self._callback_operation.__name__,
				operation_output=None,
				log_to_user=None,
				log_to_system={OP_DESCRIPTION: operation_log_str,
					OP_REFERENCES: None,
				}
			)
			log_dict = {"operation_log": operation_log}
			return FuncOutputWithLog(
				fn_output=operation_log_str,
				fn_log=log_dict,
			)

		paper_infos = list()
		for idx in indices:
			paper = results[idx]
			paper_infos.append(
				{
					"title": paper.title,
					"abstract": paper.summary,
					"pdf_url": paper.pdf_url,
				}
			)

		op_name = ArxivDownloadOperation.__name__
		kwargs = {
			"user_id": user_id,
			"paper_infos": paper_infos
		}
		kwargs_str = json.dumps(kwargs)
		operation_log = await aoperation_authorize(
			user_id=user_id,
			op_name=op_name,
			kwargs_str=kwargs_str,
			llm=self._llm,
			embed_model=self._embed_model,
			verbose=self._verbose,
		)
		log_dict = {"operation_log": operation_log}
		return FuncOutputWithLog(
			fn_output=f"Have downloaded papers for user {user_id}",
			fn_log=log_dict,
		)


if __name__ == "__main__":
	import asyncio
	from labridge.llm.models import get_models
	from labridge.tools.utils import unpack_tool_output

	llm, embed_model = get_models()
	dd = ArXivSearchDownloadTool(llm=llm, embed_model=embed_model, verbose=True)

	# tool_output = dd.call(
	# 	user_id="杨再正",
	# 	search_str="memristor",
	# )
	# tool_output, tool_log = unpack_tool_output(tool_out_json=tool_output.content)
	# tool_log = ToolLog.loads(tool_log)
	# print("to user:\n", tool_log.log_to_user)
	# print("to system:\n", tool_log.log_to_system)

	async def main():
		tool_output = await dd.acall(
			user_id="杨再正",
			search_str="reinforcement learning",
		)

		tool_output, tool_log = unpack_tool_output(tool_out_json=tool_output.content)
		tool_log = ToolLog.loads(tool_log)
		print("to user:\n", tool_log.log_to_user)
		print("to system:\n", tool_log.log_to_system)

	asyncio.run(main())
