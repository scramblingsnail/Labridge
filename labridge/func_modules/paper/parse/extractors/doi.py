import json
import numpy as np

import httpx
from httpx import AsyncClient
from typing import Optional, List, Tuple
from labridge.func_modules.paper.download.arxiv import ArxivSearcher, ArxivSearchMode


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

	def check_doi(
		self,
		title: str,
		input_doi: str,
		mismatch_tolerance: int = 5,
	) -> bool:
		r"""
		Search by the doi, check whether the title of searched result matches the input title.

		Args:
			title (str): The input paper title.
			input_doi (str): The input doi.
			mismatch_tolerance (int): The tolerance of mismatch between the input title and the title of searched result.

		Returns:
			bool: Whether the input doi match the input title according to the search results in arXiv.
		"""
		search_items = self.searcher.search(
			search_str=input_doi,
			search_mode=ArxivSearchMode.DOI,
		)
		if len(search_items) < 1:
			return False
		item = search_items[0]
		paper_title = item.title
		common_len = lcs_len(paper_title, title)
		mismatch_len = len(title) - common_len
		return mismatch_len <= mismatch_tolerance

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

	def check_doi(
		self,
		title: str,
		input_doi: str,
		mismatch_tolerance: int = 5,
	) -> bool:
		r"""
		Search by the doi, check whether the title of searched result matches the input title.

		Args:
			title (str): The input paper title.
			input_doi (str): The input doi.
			mismatch_tolerance (int): The tolerance of mismatch between the input title and the title of searched result.

		Returns:
			bool: Whether the input doi match the input title according to the search results in CrossRef.
		"""
		url = self.base_url + input_doi
		response = httpx.get(url)

		if response.status_code != 200:
			return False

		api_data = json.loads(response.text)
		paper_title = api_data["message"]["title"][0]
		common_len = lcs_len(paper_title, title)
		mismatch_len = len(title) - common_len
		return mismatch_len <= mismatch_tolerance

	def find_doi_by_title(
		self,
		title: str,
		results_num: int = 5,
		mismatch_tolerance: int = 5,
	) -> Optional[str]:
		r"""
		Find the DOI of a paper using CrossRef.
		For the construction of the search queries, refer to https://github.com/CrossRef/rest-api-doc#resource-components

		Args:
			title (str): The paper title.
			results_num (int): The top-k retrieved results are taken into consideration.
			mismatch_tolerance (int): The tolerance for mismatch between the paper title and the retrieved title.

		Returns:
			Optional[str]: The DOI of the paper. Return None if not found.
		"""
		query = f"?query.title={title}"
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
		query = f"?query.title={title}"
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
	r"""
	This class works to find the DOI of a paper through multiple approaches.

	Args:
		max_results_num (int): Maximum num of results in searching.
		title_mismatch_tolerance (int): Maximum mismatch between the searched title and the given title.
	"""
	def __init__(
		self,
		max_results_num: int = 5,
		title_mismatch_tolerance: int = 5,
	):
		self.max_results_num = max_results_num
		self.title_mismatch_tolerance = title_mismatch_tolerance
		self.crossref_worker = CrossRefWorker()
		self.arxiv_worker = ArXivWorker()

	def check_doi(
		self,
		title: str,
		input_doi: str,
		title_mismatch_tolerance: int = 5,
	) -> bool:
		r"""
		Check whether the given doi matches the title.

		Args:
			title (str): The input title.
			input_doi (str): The input doi
			title_mismatch_tolerance (int): Tolerance to the mismatch between the input title and the searched title.

		Returns:
			bool: Whether the input doi is valid.
		"""
		valid_doi = self.crossref_worker.check_doi(
			title=title,
			input_doi=input_doi,
			mismatch_tolerance=title_mismatch_tolerance,
		)
		if valid_doi:
			return valid_doi
		valid_doi = self.arxiv_worker.check_doi(
			title=title,
			input_doi=input_doi,
			mismatch_tolerance=title_mismatch_tolerance,
		)
		return valid_doi

	def find_doi_by_title(self, title: str, input_doi: str = None) -> Optional[str]:
		r"""
		Find DOI based on the given title and given doi.
		First, check whether the given doi matches the given title.

		- If they match, return the given doi.
		- If they do not match, find the corresponding doi based on the given title.

		Args:
			title (str): The given title. Obtained through methods such as extraction by LLM.
			input_doi (str): The given doi. Obtained through methods such as extraction by LLM.

		Returns:
			Optional[str]: If valid DOI found, return the DOI. Otherwise, return None.

		"""
		if input_doi:
			doi_valid = self.check_doi(
				title=title,
				input_doi=input_doi,
				title_mismatch_tolerance=self.title_mismatch_tolerance,
			)
			if doi_valid:
				return input_doi

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
	# worker = ArXivWorker()
	# my_doi = worker.find_doi_by_title(title="Towards Efficient Generative Large Language Model Serving: A Survey from Algorithms to Systems")
	# print(my_doi)


	# searcher = ArxivSearcher()
	# results = searcher.search(
	# 	search_str="Memristor",
	# 	search_mode=ArxivSearchMode.Title,
	# )
	# for r in results:
	# 	print(r.title)

	# worker = CrossRefWorker()
	# worker.check_doi(
	# 	title="",
	# 	input_doi="10.1109/wccct56755.2023.10052488",
	# )

	doi_worker = DOIWorker()
	valid = doi_worker.find_doi_by_title(
		title="CIMAX-Compiler: An End-to-End ANN Compiler for Heterogeneous Computing-in-Memory Platform",
		input_doi="10.1109/wccct56755.2023.1005248"
	)
	print("final: ", valid)

