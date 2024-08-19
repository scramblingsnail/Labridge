from arxiv import Result

from labridge.tools.interact.autorize import operation_authorize
from labridge.tools.callback import CALL_BACK_OPS
from labridge.paper.download.arxiv import ArxivDailyDownloader, ArxivSearcher
from labridge.tools.callback.paper.paper_download import ArxivDownloadOperation



def search_arxiv():


async def asearch_arxiv(user_id, search_str):
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
	print(results[1].title)
	print(results[1].pdf_url)
	print(results[1].doi)

	oper = ArxivDownloadOperation()
	dsc = oper.operation_description(
		title=results[1].title,
		abstract=results[1].summary,
	)
	print(dsc)

	await oper.ado_operation(
		user_id="杨再正",
		pdf_url=results[1].pdf_url,
		title=results[1].title,
	)
	return


if __name__ == "__main__":
	import asyncio

	arxiv_search_for_user(user_id="zhisan", search_str="memristor")

	async def other_task():
		print("It is async downloading ...")

	async def main():
		await asyncio.gather(
			arxiv_search_for_user(user_id="zhisan", search_str="memristor"),
			other_task()
		)

	asyncio.run(main())

