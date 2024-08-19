from llama_index.core.llms import LLM

from llama_index.core.indices.utils import default_parse_choice_select_answer_fn
from typing import List, Dict, Tuple

from labridge.interact.collect.types.info_base import CollectingInfoBase
from labridge.interact.collect.types.select_info import CollectingSelectInfo
from labridge.interact.prompt.collect.collect_info.prompt_keys import CollectPromptKeys
from labridge.interact.prompt.collect.modify_info.prompt_keys import ModifyPromptKeys

from labridge.interact.collect.manager.collect_manger import CollectManager
from labridge.interact.prompt.collect.collect_info.select_info import COLLECT_SELECT_INFO_PROMPT
from labridge.interact.prompt.collect.modify_info.select_info import MODIFY_SELECT_INFO_PROMPT
from labridge.interact.collect.types.select_info import SELECT_MIN_SCORE



COLLECT_SELECT_INFO_QUERY = (
	"请从可选项中选择, 作为如下信息. 您可以随时放弃本信息收集流程."
)


class SelectInfoCollector:
	def __init__(
		self,
		llm: LLM,
		required_infos: List[CollectingInfoBase],
	):
		self._llm = llm
		self._select_infos = self.get_select_infos(required_infos=required_infos)
		self._collect_manager = CollectManager(llm=llm)

	def get_select_infos(
		self,
		required_infos: List[CollectingInfoBase],
	) -> List[CollectingSelectInfo]:
		select_infos = []
		for info in required_infos:
			if isinstance(info, CollectingSelectInfo):
				select_infos.append(info)
		return select_infos

	def collect_single_info(self, info: CollectingSelectInfo) -> bool:
		# TODO: send to user:
		print("Assistant: ", self.collecting_query(info=info))

		# TODO: receive from user.
		user_response = input("User: ")

		abort = self._collect_manager.analyze_whether_abort(user_response=user_response)
		if abort:
			return abort

		predict_kwargs = {
			"prompt": COLLECT_SELECT_INFO_PROMPT,
			CollectPromptKeys.user_response_key: user_response,
		}

		all_choices, all_relevances = [], []
		for batch_info_dict, batch_candidates in info.info_content():
			predict_kwargs.update(batch_info_dict)
			raw_response = self._llm.predict(**predict_kwargs)

			raw_choices, relevances = default_parse_choice_select_answer_fn(raw_response, len(batch_candidates))
			choice_idxs = [choice - 1 for choice in raw_choices]
			batch_choices = [batch_candidates[ci] for ci in choice_idxs]

			all_choices.extend(batch_choices)
			all_relevances.extend(relevances)

		if all_choices:
			zipped_list = list(zip(all_choices, all_relevances))
			sorted_list = sorted(zipped_list, key=lambda x: x[1], reverse=True)
			collected_info, score = sorted_list[0]
			info.update_collected_info(
				collected_info_dict={info.info_name: collected_info}
			)
		return abort

	async def acollect_single_info(self, info: CollectingSelectInfo) -> bool:
		# TODO: send to user:
		print("Assistant: ", self.collecting_query(info=info))

		# TODO: receive from user.
		user_response = input("User: ")

		abort = await self._collect_manager.async_analyze_whether_abort(user_response=user_response)
		if abort:
			return abort

		predict_kwargs = {
			"prompt": COLLECT_SELECT_INFO_PROMPT,
			CollectPromptKeys.user_response_key: user_response,
		}

		all_choices, all_relevances = [], []
		for batch_info_dict, batch_candidates in info.info_content():
			predict_kwargs.update(batch_info_dict)
			raw_response = await self._llm.apredict(**predict_kwargs)

			raw_choices, relevances = default_parse_choice_select_answer_fn(raw_response, len(batch_candidates))
			choice_idxs = [choice - 1 for choice in raw_choices]
			batch_choices = [batch_candidates[ci] for ci in choice_idxs]

			all_choices.extend(batch_choices)
			all_relevances.extend(relevances)

		if all_choices:
			zipped_list = list(zip(all_choices, all_relevances))
			sorted_list = sorted(zipped_list, key=lambda x: x[1], reverse=True)
			collected_info, score = sorted_list[0]
			info.update_collected_info(
				collected_info_dict={info.info_name: collected_info}
			)
		return abort

	def collect(self) -> bool:
		for info in self._select_infos:
			abort = self.collect_single_info(info=info)
			if abort:
				return True
		return False

	async def acollect(self) -> bool:
		for info in self._select_infos:
			abort = await self.acollect_single_info(info=info)
			if abort:
				return True
		return False

	def collecting_query(self, info: CollectingSelectInfo) -> str:
		query_to_user = f"{COLLECT_SELECT_INFO_QUERY}\n"
		for key in info.collecting_keys:
			query_to_user += f"\t{key}\n"
		query_to_user += "Candidates:\n"
		for choice in info.candidates:
			query_to_user += f"\t{choice}\n"
		return query_to_user

	def modify_single_info(self, user_response: str,  info: CollectingSelectInfo):
		predict_kwargs = {
			"prompt": MODIFY_SELECT_INFO_PROMPT,
			ModifyPromptKeys.user_comment_key: user_response,
		}

		all_choices, all_possibilities = [], []
		for batch_info_dict, batch_candidates in info.modify_info_content():
			predict_kwargs.update(batch_info_dict)
			raw_response = self._llm.predict(**predict_kwargs)

			raw_choices, possibilities = default_parse_choice_select_answer_fn(raw_response, len(batch_candidates))
			choice_idxs = [choice - 1 for choice in raw_choices]
			batch_choices = [batch_candidates[ci] for ci in choice_idxs]

			all_choices.extend(batch_choices)
			all_possibilities.extend(possibilities)

		zipped_list = list(zip(all_choices, all_possibilities))
		sorted_list = sorted(zipped_list, key=lambda x: x[1], reverse=True)
		if sorted_list:
			collected_info, score = sorted_list[0]
			if score >= SELECT_MIN_SCORE:
				info.update_collected_info(
					collected_info_dict={info.info_name: collected_info}
				)

	async def amodify_single_info(self, user_response: str,  info: CollectingSelectInfo):
		predict_kwargs = {
			"prompt": MODIFY_SELECT_INFO_PROMPT,
			ModifyPromptKeys.user_comment_key: user_response,
		}

		all_choices, all_possibilities = [], []
		for batch_info_dict, batch_candidates in info.modify_info_content():
			predict_kwargs.update(batch_info_dict)
			raw_response = await self._llm.apredict(**predict_kwargs)

			raw_choices, possibilities = default_parse_choice_select_answer_fn(raw_response, len(batch_candidates))
			choice_idxs = [choice - 1 for choice in raw_choices]
			batch_choices = [batch_candidates[ci] for ci in choice_idxs]

			all_choices.extend(batch_choices)
			all_possibilities.extend(possibilities)

		zipped_list = list(zip(all_choices, all_possibilities))
		sorted_list = sorted(zipped_list, key=lambda x: x[1], reverse=True)
		if sorted_list:
			collected_info, score = sorted_list[0]
			if score >= SELECT_MIN_SCORE:
				info.update_collected_info(
					collected_info_dict={info.info_name: collected_info}
				)

	def modify(self) -> Tuple[bool, bool]:
		if len(self._select_infos) < 1:
			return False, False

		doing_modify = True
		abort = False
		while doing_modify and not abort:
			query_to_user =self._collect_manager.verify_query(collected_info_dict=self.collected_infos)
			# TODO: send the message to the user.
			print(query_to_user)

			# TODO: receive the message from the user.
			user_response = input("User: ")
			abort = self._collect_manager.analyze_whether_abort(user_response=user_response)
			if abort:
				break
			doing_modify = self._collect_manager.analyze_whether_modify(
				user_response=user_response,
				collected_info_dict=self.collected_infos
			)
			if doing_modify:
				self.single_modify(user_response=user_response)
		return doing_modify, abort

	async def amodify(self) -> Tuple[bool, bool]:
		if len(self._select_infos) < 1:
			return False, False

		doing_modify = True
		abort = False
		while doing_modify and not abort:
			query_to_user =self._collect_manager.verify_query(collected_info_dict=self.collected_infos)
			# TODO: send the message to the user.
			print(query_to_user)

			# TODO: receive the message from the user.
			user_response = input("User: ")
			abort = await self._collect_manager.async_analyze_whether_abort(user_response=user_response)
			if abort:
				break
			doing_modify = await self._collect_manager.async_analyze_whether_modify(
				user_response=user_response,
				collected_info_dict=self.collected_infos
			)
			if doing_modify:
				await self.asingle_modify(user_response=user_response)
		return doing_modify, abort


	def single_modify(self, user_response: str):
		for info in self._select_infos:
			self.modify_single_info(user_response=user_response, info=info)

	async def asingle_modify(self, user_response: str):
		for info in self._select_infos:
			await self.amodify_single_info(user_response=user_response, info=info)

	@property
	def collecting_keys(self) -> List[str]:
		collecting = []
		for info in self._select_infos:
			collecting.extend(info.collecting_keys)
		return collecting

	@property
	def collected_infos(self) -> Dict[str, str]:
		infos = {}
		for info in self._select_infos:
			infos.update(info.collected_infos)
		return infos

	@property
	def collected(self):
		for info in self._select_infos:
			if not info.collected:
				return False
		return True
