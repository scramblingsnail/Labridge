import json
import numpy as np

import httpx
from httpx import AsyncClient
from typing import Optional, List, Tuple
from labridge.func_modules.paper.download.arxiv import ArxivSearcher


CROSSREF_BASE_URL = "https://api.crossref.org/works/"
MAX_REQUEST_TRY = 5
MISMATCH_TOLERANCE = 5


def lcs_len(str1: str, str2: str) -> int:
	len1 = len(str1)
	len2 = len(str2)
	len_array = np.zeros((len1 + 1, len2 + 1), dtype=int)

	for i in range(1, len1 + 1):
		for j in range(1, len2 + 1):
			if str1[i - 1] == str2[j - 1]:
				len_array[i][j] = len_array[i - 1][j - 1] + 1
			else:
				len_array[i][j] = max(len_array[i - 1][j], len_array[i][j - 1])
	return len_array[-1][-1]


class ArXivWorker(object):
	r"""
	This is a worker using the arXiv API to obtain the DOI of a paper.

	If the found paper has no DOI yet, use the entry_id of arXiv instead.
	"""
	def __init__(self):
		self.searcher = ArxivSearcher()

	def find_doi_by_title(
		self,
		title: str,
		results_num: int = 5,
		mismatch_tolerance: int = 5,
	) -> Optional[str]:
		search_items = self.searcher.search(search_str=title, max_results_num=results_num)
		match_results: List[Tuple[int, int]] = []
		for idx, item in enumerate(search_items):
			paper_title = item.title
			common_len = lcs_len(paper_title, title)
			mismatch_len = len(title) - common_len
			match_results.append((idx, mismatch_len))

		match_results.sort(key=lambda x: x[1])
		if match_results[0][1] > mismatch_tolerance:
			return None
		match_idx = match_results[0][0]
		match_paper = search_items[match_idx]
		doi = match_paper.doi
		entry_id = match_paper.entry_id

		if doi:
			return doi
		return entry_id


class CrossRefWorker(object):
	r"""
	This is a worker using the CrossRef API to obtain the DOI of a paper.

	Refer to https://www.crossref.org/documentation/retrieve-metadata/rest-api/
	"""
	def __init__(
		self,
		base_url: str = CROSSREF_BASE_URL,
	):
		self.base_url = base_url
		self.async_client = AsyncClient()

	def _get_doi_from_api_data(
		self,
		title: str,
		api_data: dict,
		results_num: int = 5,
		mismatch_tolerance: int = MISMATCH_TOLERANCE,
	):
		items = api_data["message"]["items"]
		match_results = []
		for idx, item in enumerate(items[: results_num]):
			title_msg = item.get("title", None)
			if title_msg is None:
				match_results.append((idx, MISMATCH_TOLERANCE + 1))
				continue
			common_len = lcs_len(item["title"][0], title)
			mismatch_len = len(title) - common_len
			match_results.append((idx, mismatch_len))

		match_results.sort(key=lambda x: x[1])
		if match_results[0][1] > mismatch_tolerance:
			return None
		match_idx = match_results[0][0]

		try:
			doi = items[match_idx]["DOI"]
			return doi
		except KeyError:
			return None

	def find_doi_by_title(
		self,
		title: str,
		results_num: int = 5,
		mismatch_tolerance: int = 5,
	) -> Optional[str]:
		r"""
		Find the DOI of a paper using CrossRef.

		Args:
			title (str): The paper title.
			results_num (int): The top-k retrieved results are taken into consideration.
			mismatch_tolerance (int): The tolerance for mismatch between the paper title and the retrieved title.

		Returns:
			Optional[str]: The DOI of the paper. Return None if not found.
		"""
		query = f"?query={title}"
		url = self.base_url + query

		try_times = 0
		response = None
		while try_times < MAX_REQUEST_TRY:
			try:
				response = httpx.get(url)
				break
			except:
				try_times += 1

		if response is None:
			return None
		api_data = json.loads(response.text)
		doi = self._get_doi_from_api_data(
			title=title,
			api_data=api_data,
			results_num=results_num,
			mismatch_tolerance=mismatch_tolerance,
		)
		return doi

	async def afind_doi_by_title(
		self,
		title: str,
		results_num: int = 5,
		mismatch_tolerance: int = 5,
	) -> Optional[str]:
		r"""
		Asynchronously find the DOI of a paper using CrossRef.

		Args:
			title (str): The paper title.
			results_num (int): The top-k retrieved results are taken into consideration.
			mismatch_tolerance (int): The tolerance for mismatch between the paper title and the retrieved title.

		Returns:
			Optional[str]: The DOI of the paper. Return None if not found.
		"""
		query = f"?query={title}"
		url = self.base_url + query

		try_times = 0
		response = None
		while try_times < MAX_REQUEST_TRY:
			try:
				response = await self.async_client.get(url=url)
				break
			except:
				try_times += 1
		api_data = json.loads(response.text)
		doi = self._get_doi_from_api_data(
			title=title,
			api_data=api_data,
			results_num=results_num,
			mismatch_tolerance=mismatch_tolerance,
		)
		return doi


class DOIWorker(object):
	def __init__(
		self,
		max_results_num: int = 5,
		title_mismatch_tolerance: int = 5,
	):
		self.max_results_num = max_results_num
		self.title_mismatch_tolerance = title_mismatch_tolerance
		self.crossref_worker = CrossRefWorker()
		self.arxiv_worker = ArXivWorker()

	def find_doi_by_title(self, title: str) -> Optional[str]:
		doi = self.crossref_worker.find_doi_by_title(
			title=title,
			results_num=self.max_results_num,
			mismatch_tolerance=self.title_mismatch_tolerance,
		)
		if doi:
			return doi

		doi = self.arxiv_worker.find_doi_by_title(
			title=title,
			results_num=self.max_results_num,
			mismatch_tolerance=self.title_mismatch_tolerance,
		)
		return doi


if __name__ == "__main__":
	worker = ArXivWorker()
	my_doi = worker.find_doi_by_title(title="Towards Efficient Generative Large Language Model Serving: A Survey from Algorithms to Systems")
	print(my_doi)
