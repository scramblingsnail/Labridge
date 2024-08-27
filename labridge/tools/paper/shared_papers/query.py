r"""
All functions in this file need the authorization of the users before execution.

All Interactions should be returned as tool output.
"""

from labridge.tools.base.tool_base import QueryEngineBaseTool
from labridge.tools.base.tool_log import ToolLog, TOOL_OP_DESCRIPTION, TOOL_REFERENCES
from labridge.func_modules.reference.paper import PaperInfo
from labridge.func_modules.paper.query_engine.paper_query_engine import (
	PaperQueryEngine,
	PAPER_QUERY_TOOL_NAME,
	PAPER_QUERY_TOOL_DESCRIPTION,
)

from typing import List


class PaperQueryTool(QueryEngineBaseTool):
	r"""
	This tool is used to answer the query with access to the shared paper storage.
	"""
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

	def log(self) -> ToolLog:
		r"""
		Get the log: specifically, the references.
		"""
		ref_infos: List[PaperInfo] = self.query_engine.get_ref_info()

		log_to_user = None
		log_to_system = {
			TOOL_OP_DESCRIPTION: f"User the {self.metadata.name} to answer the user's query.",
			TOOL_REFERENCES: [ref_info.dumps() for ref_info in ref_infos]
		}
		return ToolLog(
			tool_name=self.metadata.name,
			log_to_user=log_to_user,
			log_to_system=log_to_system,
		)
