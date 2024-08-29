import json

import fsspec
import asyncio

from llama_index.core.utils import print_text
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core import Settings
from llama_index.core.llms import LLM
from labridge.callback.base.operation_base import CallBackOperationBase
from labridge.callback.base.operation_log import OperationOutputLog, OP_DESCRIPTION, OP_REFERENCES

from pathlib import Path
from typing import Tuple, Optional, List

from labridge.func_modules.paper.download.arxiv import Result
from labridge.func_modules.paper.store.temporary_store import TMP_PAPER_WAREHOUSE_DIR
from labridge.func_modules.paper.download.async_utils import adownload_file
from labridge.func_modules.paper.store.temporary_store import RecentPaperStore
from labridge.func_modules.reference.paper import PaperInfo


ARXIV_DOWNLOAD_OPERATION_NAME = "ArxivDownloadOperation"


ARXIV_DOWNLOAD_DESCRIPTION = \
"""
为 {user_id} 从arXiv下载如下文献, 并加入ta的临时文献库:
"""

PAPER_DESCRIPTION_TMPL = \
"""
**标题**: {title}
**存储路径**: {save_path}
"""

ARXIV_DOWNLOADING_STR = \
"""
正在为您从 aXiv 下载文献 ...
"""


class ArxivDownloadOperation(CallBackOperationBase):
	r"""
	This operation will download papers from aXiv for the user.

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
		super().__init__(
			llm=llm,
			embed_model=embed_model,
			verbose=verbose,
			op_name=op_name or ArxivDownloadOperation.__name__,
		)

	def _get_default_path(self, user_id: str, title: str) -> Tuple[str, str]:
		r"""
		The downloaded paper will be stored in the user's recent paper warehouse.

		Args:
			user_id (str): The user id of a lab member.
			title (str): The title of the paper, will be used as the filename.

		Returns:
			Tuple[str, str]:
				The paper file path and file name.
		"""
		file_name = f"{title}.pdf"
		file_dir = self.root / TMP_PAPER_WAREHOUSE_DIR
		file_dir = file_dir / user_id

		if not self._fs.exists(file_dir):
			self._fs.makedirs(file_dir)
		return str(file_dir), file_name

	def operation_description(self, **kwargs) -> str:
		r"""
		Describe the operation.

		Args:
			user_id (str): the user id.
			paper_infos (List[Dict[str, str]]): the metadata of papers,
				for each paper, the `title` must be provided.

		Returns:
			the operation description.
		"""
		user_id = kwargs.get("user_id", None)
		paper_infos = kwargs.get("paper_infos", None)

		if None in [user_id, paper_infos]:
			raise ValueError("should provide valid user_id, paper_infos.")

		papers = []
		for paper in paper_infos:
			title = paper.get("title", None)
			file_dir, file_name = self._get_default_path(user_id=user_id, title=title)
			save_path = str(Path(file_dir) / file_name)
			paper_dsc = PAPER_DESCRIPTION_TMPL.format(title=title, save_path=save_path)
			papers.append(paper_dsc)
		papers = "\n\n".join(papers)
		header = ARXIV_DOWNLOAD_DESCRIPTION.format(user_id=user_id)
		description = f"{header}\n{papers}"
		return description

	def download_paper(self, user_id: str, title: str, pdf_url: str) -> Optional[str]:
		r"""
		Download a paper from arxiv and save to the user's recent paper directory.

		Args:
			user_id (str): The user id of a lab member.
			title (str): The paper title.
			pdf_url (str): The paper URL.

		Returns:
			Optional[str]:

				- If the paper is successfully downloaded, return the file_path.
				- If the downloading fails, return None.
		"""
		if None in [user_id, title, pdf_url]:
			raise ValueError("should provide valid user_id, title, pdf_url to download paper.")
		file_dir, file_name = self._get_default_path(user_id=user_id, title=title)
		result = Result(entry_id="")
		result.pdf_url = pdf_url

		if self._verbose:
			print_text(text=f"Downloading paper '{title}' ...", color="pink", end="\n")

		try:
			result.download_pdf(dirpath=file_dir, filename=file_name)
			file_path = str(Path(file_dir) / file_name)
			return file_path
		except Exception as e:
			print(f"Download failed. Error: {e}")
			return None

	async def adownload_paper(self, user_id: str, title: str, pdf_url: str) -> Optional[str]:
		r"""
		Asynchronously download a paper from arxiv and save to the user's recent paper directory.
		"""
		if None in [user_id, title, pdf_url]:
			raise ValueError("should provide valid user_id, title, pdf_url to download paper.")

		file_dir, file_name = self._get_default_path(user_id=user_id, title=title)
		file_path = str(Path(file_dir) / file_name)

		if self._verbose:
			print_text(text=f"Downloading paper '{title}' ...", color="pink", end="\n")
		try:
			await adownload_file(url=pdf_url, save_path=file_path)
			return file_path
		except Exception as e:
			print(f"Download failed. Error: {e}")
			return None

	def _get_log(
		self,
		user_id: str,
		succeed_papers: List[Tuple[str, str]],
		fail_papers: List[str]
	) -> OperationOutputLog:
		r""" Get the operation log. """
		logs = []
		if succeed_papers:
			logs.append(f"Successfully download these papers, and restore them in the recent papers of user {user_id}:")

		ref_paper_infos = []

		for title, file_path in succeed_papers:
			download_log = {
				"Title": title,
				"Save path": file_path,
			}
			download_log_str = json.dumps(download_log)
			logs.append(download_log_str)
			paper_info = PaperInfo(
				title=title,
				file_path=file_path,
				possessor=user_id,
			)
			ref_paper_infos.append(paper_info.dumps())

		if fail_papers:
			failed_log = "These paper downloading failed:\n"
			failed_log += "\n".join(fail_papers)
			logs.append(failed_log)
		log_str = "\n\n".join(logs)
		return OperationOutputLog(
			operation_name=self.op_name,
			operation_output=None,
			log_to_user=None,
			log_to_system={
				OP_DESCRIPTION: log_str,
				OP_REFERENCES: ref_paper_infos,
			}
		)

	def do_operation(self, **kwargs) -> OperationOutputLog:
		r"""
		Execute the downloading operation and return the log string.

		Args:
			user_id (str): the user id.
			paper_infos (List[Dict[str, str]]): the metadata of papers,
				for each paper, the `title` and `pdf_url` must be provided

		Returns:
			OperationLog:
				The operation output and log.
		"""
		user_id = kwargs.get("user_id", None)
		paper_infos = kwargs.get("paper_infos", [])

		if None in [user_id, paper_infos]:
			raise ValueError("These arguments must be provided: user_id, paper_infos.")

		if not isinstance(paper_infos, list):
			paper_infos = [paper_infos]

		tmp_paper_store = RecentPaperStore.from_user_id(
			user_id=user_id,
			embed_model=self._embed_model,
		)

		succeed, fail = [], []

		for info in paper_infos:
			pdf_url = info.get("pdf_url", None)
			title = info.get("title", None)
			file_path = self.download_paper(
				user_id=user_id,
				title=title,
				pdf_url=pdf_url,
			)
			if file_path is None:
				fail.append(title)
			else:
				succeed.append((title, file_path))
				tmp_paper_store.put(paper_file_path=file_path)

		tmp_paper_store.persist()
		output_log = self._get_log(user_id=user_id, succeed_papers=succeed, fail_papers=fail)
		return output_log

	async def ado_operation(self, **kwargs) -> OperationOutputLog:
		r"""
		Asynchronously do the downloading operation and return the log string.

		Args:
			user_id (str): the user id.
			paper_infos (List[Dict[str, str]]): the metadata of papers,
				for each paper, the `title` and `pdf_url` must be provided

		Returns:
			str:
				The operation output and log.
		"""
		user_id = kwargs.get("user_id", None)
		paper_infos = kwargs.get("paper_infos", [])

		if None in [user_id, paper_infos]:
			raise ValueError("These arguments must be provided: user_id, paper_infos.")

		if not isinstance(paper_infos, list):
			paper_infos = [paper_infos]

		tmp_paper_store = RecentPaperStore.from_user_id(
			user_id=user_id,
			embed_model=self._embed_model,
		)

		succeed, fail = [], []

		async def single_op(info):
			pdf_url = info.get("pdf_url", None)
			title = info.get("title", None)
			file_path = await self.adownload_paper(
				user_id=user_id,
				title=title,
				pdf_url=pdf_url,
			)
			if file_path is None:
				fail.append(title)
			else:
				succeed.append((title, file_path))
				tmp_paper_store.put(paper_file_path=file_path)

		task_list = tuple([asyncio.create_task(single_op(paper_info)) for paper_info in paper_infos])
		await asyncio.gather(*task_list)
		tmp_paper_store.persist()
		output_log = self._get_log(user_id=user_id, succeed_papers=succeed, fail_papers=fail)
		return output_log


if __name__ == "__main__":
	import asyncio

	dd = ArxivDownloadOperation(verbose=True)

	paper_infos = [
		{
			"pdf_url": 'http://arxiv.org/pdf/1101.4618v1',
			"title": 'Chaotic memristor',
		},
		{
			"pdf_url": 'http://arxiv.org/pdf/1511.02192v2',
			"title": 'Quantum Memristors',
		}
	]

	async def main():
		await dd.ado_operation(
			user_id="杨再正",
			paper_infos=paper_infos,
		)

	asyncio.run(main())



