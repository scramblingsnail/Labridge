from arxiv import Result

from labridge.paper.download.arxiv import ArxivDailyDownloader, ArxivSearcher



def arxiv_daily_paper_for_user(user_id, ):
	return


def arxiv_search_for_user(user_id, search_str):
	r"""
	Search in the arxiv, the results will be added to the temporary paper index.

	This tmp paper info index should include:

	- Search_date: used to delete.
	- Title
	- Abstract
	- Authors
	- arxiv_entry_id
	- doi
	- pdf_url: use urllib.request to obtain.
	- journal_ref
	"""
	searcher = ArxivSearcher()
	results = searcher.search(search_str)
	print("begin: ")
	for result in results:
		print(result.title)
		print(result.pdf_url)
		print(result.doi)
	return


if __name__ == "__main__":
	arxiv_search_for_user(user_id="zhisan", search_str="memristor")

