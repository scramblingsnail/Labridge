import json

from typing import Dict


from llama_index.core.llms import LLM

from labridge.interact.prompt.collect.manager.verify import VERIFY_COLLECTED_INFO_QUERY
from labridge.interact.collect.utils import condition_analyze, acondition_analyze

from labridge.interact.prompt.collect.manager.abort import (
	COLLECT_ABORT_PROMPT,
	COLLECT_ABORT_WORD,
	COLLECT_CONTINUE_WORD,
)

from labridge.interact.prompt.collect.manager.do_modify import (
	DO_MODIFY_WORD,
	NOT_MODIFY_WORD,
	WHETHER_MODIFY_INFO_PROMPT,
)


class CollectManager:
	r"""
	This manager judges whether to abort the collecting process according to the user's response,
	and whether the collected information need modification.

	Args:
		llm (LLM): The used LLM.
	"""
	def __init__(
		self,
		llm: LLM,
	):
		self._llm = llm

	def analyze_whether_abort(self, user_response: str) -> bool:
		r"""
		Whether the user tends to abort.

		Args:
			user_response (str): The user's response.

		Returns:
			bool: Whether to abort or not.
		"""
		abort = condition_analyze(
			llm=self._llm,
			prompt=COLLECT_ABORT_PROMPT,
			condition_true_word=COLLECT_ABORT_WORD,
			abort_word=COLLECT_ABORT_WORD,
			continue_word=COLLECT_CONTINUE_WORD,
			user_response=user_response,
		)
		return abort

	async def async_analyze_whether_abort(self, user_response: str) -> bool:
		r"""
		Async version.
		Whether the user tends to abort.

		Args:
			user_response (str): The user's response.

		Returns:
			bool: Whether to abort or not.
		"""
		abort = await acondition_analyze(
			llm=self._llm,
			prompt=COLLECT_ABORT_PROMPT,
			condition_true_word=COLLECT_ABORT_WORD,
			abort_word=COLLECT_ABORT_WORD,
			continue_word=COLLECT_CONTINUE_WORD,
			user_response=user_response,
		)
		return abort

	async def async_analyze_whether_modify(
		self,
		user_response: str,
		collected_info_dict: Dict[str, str],
	) -> bool:
		r"""
		Async version.
		Whether the user thinks the collected information need modification.

		Args:
			user_response (str): The user's response.

		Returns:
			bool: Whether to modify or not.
		"""
		do_modify = await acondition_analyze(
			llm=self._llm,
			prompt=WHETHER_MODIFY_INFO_PROMPT,
			condition_true_word=DO_MODIFY_WORD,
			do_modify_word=DO_MODIFY_WORD,
			not_modify_word=NOT_MODIFY_WORD,
			collected_infos_str=json.dumps(collected_info_dict),
			user_comment_str=user_response,
		)
		return do_modify

	def analyze_whether_modify(
		self,
		user_response: str,
		collected_info_dict: Dict[str, str],
	) -> bool:
		r"""
		Whether the user thinks the collected information need modification.

		Args:
			user_response (str): The user's response.

		Returns:
			bool: Whether to modify or not.
		"""
		do_modify = condition_analyze(
			llm=self._llm,
			prompt=WHETHER_MODIFY_INFO_PROMPT,
			condition_true_word=DO_MODIFY_WORD,
			do_modify_word=DO_MODIFY_WORD,
			not_modify_word=NOT_MODIFY_WORD,
			collected_infos_str=json.dumps(collected_info_dict),
			user_comment_str=user_response,
		)
		return do_modify

	def verify_query(self, collected_info_dict: Dict[str, str]) -> str:
		r""" This query will be sent to the user to verify the correctness of the collected information. """
		verify_str = f"{VERIFY_COLLECTED_INFO_QUERY}\n"
		for key in collected_info_dict.keys():
			verify_str += f"{key}:\n\t{collected_info_dict[key]}\n"
		return verify_str
