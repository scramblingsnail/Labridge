import arxiv
import datetime

from llama_index.readers.web import SimpleWebPageReader
from urllib.parse import urlencode
from arxiv import Search, Client, SortCriterion, Result
from labridge.paper.download.arxiv import ArxivCategory, ArxivClient, ArxivDailyDownloader


dd = ArxivDailyDownloader()
# daily_papers = dd.get_daily_papers_info(relevant_categories=["cs.AI"])
# print(daily_papers)


# cc = ArxivCategory()
# print(cc.category)