r"""
All functions in this file need the authorization of the users before execution.

All Interactions should be returned as tool output.
"""

import json

from ..base import QueryEngineBaseTool
from labridge.paper.query_engine.paper_query_engine import (
	PaperQueryEngine,
	PAPER_QUERY_TOOL_NAME,
	PAPER_QUERY_TOOL_DESCRIPTION,
)


class PaperQueryTool(QueryEngineBaseTool):
	def __init__(
		self,
		paper_query_engine: PaperQueryEngine,
		name=PAPER_QUERY_TOOL_NAME,
		description=PAPER_QUERY_TOOL_DESCRIPTION,
	):
		super().__init__(
			query_engine=paper_query_engine,
			name=name,
			description=description,
		)

	def log(self) -> str:
		r"""
		Get the log: specifically, the references.
		"""
		ref_info = self.query_engine.get_ref_info()
		return json.dumps(ref_info)


def insert_new_paper(user_id: str, paper_path: str):
	r""" Need the authorization """
	return


def _find_proper_dir(user_id: str, ):
	r"""
	Need to ask for the user's suggestion.

	When processing the user's suggestion, need to find the correct valid dir:
	the DirSummaryIndex in paper store need a new methods to match the most relevant dir.

	"""
	return
