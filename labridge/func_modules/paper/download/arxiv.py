import json
import fsspec
import datetime

from llama_index.readers.web import SimpleWebPageReader
from pathlib import Path
from arxiv import Search, Client, SortCriterion, SortOrder, Result
from typing import Optional, List, Dict


ARXIV_CATEGORY_PATH = "documents/cfgs/research_category.json"

Extra_Descriptions = {
	"Computer Science": {
		"cs.ET": "\nIncluding emerging computing technologies, "
				 "such as computing-in-memory hardware (ReRAM, SRAM, etc.)"
	}
}


class ArxivClient(Client):
	r"""
	Similar to the class `Client` in the package `arxiv`.
	The method `_format_url` is corrected here to enable advanced search.

	For details about advanced search in arXiv, refer to
	[Details of Query Construction](https://info.arxiv.org/help/api/user-manual.html#query_details)

	Advanced search fields:
	|	prefix	|	explanation		|
	|:--------:|:-----------------:|
	|ti		|Title				|
	|au		|Author				|
	|abs		|Abstract			|
	|co		|Comment			|
	|jr		|Journal Reference	|
	|cat		|Subject Category	|
	|rn		|Report Number		|
	|id_list	|Id list			|
	|all		|All of the above	|
	"""

	page_size: int
	"""
	Maximum number of results fetched in a single API request. Smaller pages can
	be retrieved faster, but may require more round-trips.

	The API's limit is 2000 results per page.
	"""
	delay_seconds: float
	"""
	Number of seconds to wait between API requests.

	[arXiv's Terms of Use](https://arxiv.org/help/api/tou) ask that you "make no
	more than one request every three seconds."
	"""
	num_retries: int
	"""
	Number of times to retry a failing API request before raising an Exception.
	"""
	def __init_(self, page_size: int = 100, delay_seconds: float = 3.0, num_retries: int = 3):
		super().__init__(
			page_size=page_size,
			delay_seconds=delay_seconds,
			num_retries=num_retries
		)

	def query_format(self, url_args: dict) -> str:
		r""" Formatted url for searching in arXiv. """
		query = url_args["search_query"]
		suffix = f"search_query={query}"
		for key in url_args.keys():
			if key != "search_query":
				suffix += f"&{key}={url_args[key]}"
		return self.query_url_format.format(suffix)

	def _format_url(self, search: Search, start: int, page_size: int) -> str:
		r""" Formatted url for searching in arXiv. """
		url_args = search._url_args()
		url_args.update(
			{
				"start": start,
				"max_results": page_size,
			}
		)
		return self.query_format(url_args)


class ArxivCategory(object):
	r"""
	The research fields category from arXiv.

	Attributes:
		category (dict): a dict containing sub dicts.
			- key: the research fields group name.
			- value: a sub dict containing the research fields categories.
			Each sub dict contains:

				- key: the research fields category name.
				- value: the description of this category.
		persist_path (str): the storing path of the category dict.
		arxiv_category_url (str): the url of the arxiv category.

	Args:
		persist_path (str): the storing path of the category dict.
	"""
	category: dict
	persist_path: str
	arxiv_category_url: str = "https://arxiv.org/category_taxonomy"

	def __init__(self, persist_path: Optional[str] = None):
		self.persist_path = persist_path or self._default_persist_path()
		if Path(self.persist_path).exists():
			self.category = self.load_category()
		else:
			self.category = self.category_from_arxiv()
			self.save_category()

	def _default_persist_path(self) -> str:
		r""" Default persist path. """
		root = Path(__file__)
		for i in range(5):
			root = root.parent
		return str(root / ARXIV_CATEGORY_PATH)

	def category_from_arxiv(self, arxiv_category_url: Optional[str] = None) -> dict:
		r"""
		Parse categories from arxiv.

		Args:
			arxiv_category_url (Optional[str]): Generally, the url is "https://arxiv.org/category_taxonomy".

		Returns:
			dict: The category dict in the following format:
				`{Group: {Category: description (str)}}`
		"""
		arxiv_category_url = arxiv_category_url or self.arxiv_category_url
		web_reader = SimpleWebPageReader(html_to_text=True)
		web_text = web_reader.load_data([arxiv_category_url])
		text = web_text[0].text
		fields_str = text.split("Category description if available")[1]
		fields_dict= dict()
		line_list = fields_str.split('\n')

		description = []
		group = None
		category = None
		for line in line_list:
			line_items = line.split()
			if line_items and line_items[0] == "##":
				group = " ".join(line_items[1:])
				fields_dict[group] = {}
				category = None
			elif line_items and line_items[0] == "####":
				if category is not None:
					fields_dict[group][category] = " ".join(description)
				category = line_items[1]
				description = [f"{' '.join(line_items[2:])}:"]
			else:
				description.append(line)

		fields_dict[group][category] = " ".join(description)

		# Extra information.
		for group in Extra_Descriptions.keys():
			for category in Extra_Descriptions[group].keys():
				fields_dict[group][category] += Extra_Descriptions[group][category]

		return fields_dict

	def load_category(self, persist_path: Optional[str] = None, fs: Optional[fsspec.AbstractFileSystem] = None):
		"""Load the research categories from a persist path."""
		fs = fs or fsspec.filesystem("file")
		persist_path = persist_path or self.persist_path
		with fs.open(persist_path, "rb") as f:
			category = json.load(f)
		return category

	def save_category(self, persist_path: Optional[str] = None, fs: Optional[fsspec.AbstractFileSystem] = None):
		"""Save the research categories from a persist path."""
		persist_path = persist_path or self.persist_path
		fs = fs or fsspec.filesystem("file")
		dirpath = str(Path(persist_path).parent)
		if not fs.exists(dirpath):
			fs.makedirs(dirpath)

		with fs.open(persist_path, "w") as f:
			f.write(json.dumps(self.category))


class ArxivDailyDownloader(object):
	r"""
	Get the recent relevant papers on arXiv.

	Attributes:
		category (ArxivCategory): Storing the research fields categories.
		client (ArxivClient): For Fetching papers.
		recent_days (int): papers dating back to `recent_days` ago from today will be obtained.
	"""

	category: ArxivCategory
	client: ArxivClient
	recent_days: int

	def __init__(self, recent_days: int = 1):
		self.today = datetime.date.today()
		self.category = ArxivCategory()
		self.client = ArxivClient()
		self.recent_days = recent_days
		self.search = Search(
			query="cat:cs.AI",
			sort_by=SortCriterion.SubmittedDate,
			sort_order=SortOrder.Descending,
		)

	def _is_valid_category(self, cat: str) -> bool:
		r"""
		Check if the category is valid

		Args:
			cat (str): a research category.

		Returns:
			bool: Whether the given category is a valid category in arXiv.
		"""
		cat_dict = self.category.category
		for group in cat_dict.keys():
			if cat in cat_dict[group].keys():
				return True
		return False

	def _valid_date(self, date: datetime.date, start_date: datetime.date, end_date: datetime.date) -> bool:
		r""" Check if the date is 'recent' """
		return start_date <= date <= end_date

	def get_daily_papers_info(self, relevant_categories: List[str]) -> List[Result]:
		r"""
		Get the recent papers relevant to the input categories.

		The information (e.g. Abstract, Title, Authors) of these daily papers will be sent to
		the corresponding Lab Members. The papers selected by the members will be parsed and stored
		into a proper directory.

		Args:
			relevant_categories (List[str]): The recent papers in these categories will be counted.

		Return:
			List[Result]: Recent papers information.
		"""
		query = ""
		for cat in relevant_categories:
			if self._is_valid_category(cat):
				if len(query) > 0:
					query += "+OR+"
				query += f"cat:{cat}"

		daily_papers = []
		if len(query) == 0:
			return daily_papers

		self.search.query = query
		start_date = self.today - datetime.timedelta(days=self.recent_days)
		for result in self.client.results(search=self.search):
			submit_date = result.published
			if not self._valid_date(date=submit_date, start_date=start_date, end_date=self.today):
				break
			daily_papers.append(result)
		return daily_papers

	def download_papers(self, paper_dict: Dict[Result, str]):
		r"""
		Download the selected papers.

		Args:
			paper_dict (Dict[Result, str]):
				- key: paper (Result)
				- value: save_dir (str)
		"""
		for paper in paper_dict.keys():
			paper.download_pdf(dirpath=paper_dict[paper], filename=f"{paper.title}.pdf")


class ArxivSearcher(object):
	r"""
	This class searches for papers in the arxiv.

	Attributes:
		max_results_num (int): Maximum number of results in a search.
		category (ArxivCategory): The arXiv research category.
		client (ArxivClient): Client responsible for searching.
		searcher (Search): The parameters of searching.
	"""
	def __init__(self, max_results_num: int = 5):
		self.max_results_num = max_results_num
		self.category = ArxivCategory()
		self.client = ArxivClient()
		self.searcher = Search(
			query="",
			sort_by=SortCriterion.Relevance,
			sort_order=SortOrder.Descending,
		)

	def search(self, search_str: str, max_results_num: int = None) -> List[Result]:
		r"""
		Search according to the title or abstract.

		Args:
			search_str (str): The search string, typically the title or abstract.
			max_results_num (int): Maximum num of results. Defaults to None.

		Returns:
			List[Result]: The search results.
		"""
		# query = f"ti:{search_str}+OR+abs:{search_str}"
		query = f"ti:{search_str}"
		self.searcher.query = query
		max_results_num = max_results_num or self.max_results_num
		count = 0
		results = []
		for result in self.client.results(search=self.searcher):
			count += 1
			results.append(result)
			if count >= max_results_num:
				break
		return results
