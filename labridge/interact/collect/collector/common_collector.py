import json
import copy

from llama_index.core.settings import Settings
from llama_index.core.llms import LLM
from llama_index.core.prompts.base import PromptTemplate, PromptType
from llama_index.core.indices.utils import default_parse_choice_select_answer_fn
from typing import List, Dict, Optional, Tuple

from labridge.llm.models import get_models

from labridge.tools.interact.prompt.collect_select import COLLECT_CHOICE_SELECT_PROMPT, MODIFY_CHOICE_SELECT_PROMPT


from labridge.tools.interact.types import (
	CollectingInfoBase, CollectingInfoType, CollectPromptKeys, COMMON_COLLECT_BATCH_SIZE, SELECT_CHOICE_BATCH_SIZE,
	CollectingCommonInfo, CollectingSelectInfo, ModifyPromptKeys, SELECT_MIN_SCORE
)




class CommonInfoCollector:
	def __init__(
		self,
		llm: LLM,
		required_infos: List[CollectingInfoBase],
	):
		self._llm = llm
		self._common_infos = self.get_common_infos(required_infos=required_infos)
		self._collect_manager = CollectManager(llm=llm)

	def get_common_infos(
		self,
		required_infos: List[CollectingInfoBase],
	) -> CollectingCommonInfo:
		common_info = None
		for info in required_infos:
			if isinstance(info, CollectingCommonInfo):
				if common_info is None:
					common_info = copy.deepcopy(info)
				else:
					common_info.insert_info(info)
		return common_info

	@property
	def collecting_keys(self) -> Optional[List[str]]:
		if self._common_infos is None:
			return None

		return self._common_infos.collecting_keys

	@property
	def collected_infos(self) -> Optional[Dict[str, str]]:
		if self._common_infos is None:
			return None

		return self._common_infos.collected_infos

	@property
	def collected(self):
		if self._common_infos is None:
			return True

		return self._common_infos.collected

	@property
	def collecting_query(self) -> str:
		query_to_user = f"{COLLECT_INFO_QUERY}\n"
		for key in self.collecting_keys:
			query_to_user += f"\t{key}\n"
		return query_to_user

	def collect(self) -> bool:
		if self._common_infos is None:
			return False

		query_to_user = self.collecting_query
		# TODO: send the message to the user.
		print(query_to_user)

		# TODO: receive the message from the user.
		user_response = input("User: ")
		abort = self._collect_manager.analyze_whether_abort(user_response=user_response)
		if abort:
			return abort

		info_type = self._common_infos.info_type
		info_prompt = COLLECT_PROMPT_DICT[info_type]
		for batch_info_dict in self._common_infos.info_content():
			predict_kwargs = {
				"prompt": info_prompt,
				CollectPromptKeys.user_response_key: user_response,
			}
			predict_kwargs.update(batch_info_dict)
			extract_info = self._llm.predict(**predict_kwargs)
			new_info_dict = parse_common_collected_info(
				extract_info=extract_info,
				info_keys=self._common_infos.collecting_keys,
			)
			self._common_infos.update_collected_info(collected_info_dict=new_info_dict)
		return abort

	async def acollect(self) -> bool:
		if self._common_infos is None:
			return False

		query_to_user = self.collecting_query
		# TODO: send the message to the user.
		print(query_to_user)

		# TODO: receive the message from the user.
		user_response = input("User: ")

		abort = await self._collect_manager.async_analyze_whether_abort(user_response=user_response)
		if abort:
			return abort

		info_type = self._common_infos.info_type
		info_prompt = COLLECT_PROMPT_DICT[info_type]
		for batch_info_dict in self._common_infos.info_content():
			predict_kwargs = {
				"prompt": info_prompt,
				CollectPromptKeys.user_response_key: user_response,
			}
			predict_kwargs.update(batch_info_dict)
			extract_info = await self._llm.apredict(**predict_kwargs)
			new_info_dict = parse_common_collected_info(
				extract_info=extract_info,
				info_keys=self._common_infos.collecting_keys,
			)
			self._common_infos.update_collected_info(collected_info_dict=new_info_dict)
		return abort

	def modify(self) -> Tuple[bool, bool]:
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
		doing_modify = True
		abort = False
		while doing_modify and not abort:
			query_to_user = self._collect_manager.verify_query(collected_info_dict=self.collected_infos)
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
		info_type = self._common_infos.info_type
		modify_prompt = MODIFY_PROMPT_DICT[info_type]
		for batch_info_dict in self._common_infos.modify_info_content():
			predict_kwargs = {
				"prompt": modify_prompt,
				ModifyPromptKeys.user_comment_key: user_response,
			}
			predict_kwargs.update(batch_info_dict)
			extract_info = self._llm.predict(**predict_kwargs)
			new_info_dict = parse_common_collected_info(
				extract_info=extract_info,
				info_keys=list(self._common_infos.required_infos.keys()),
			)
			print("modified: ", new_info_dict)
			self._common_infos.update_collected_info(collected_info_dict=new_info_dict)

	async def asingle_modify(self, user_response: str):
		info_type = self._common_infos.info_type
		modify_prompt = MODIFY_PROMPT_DICT[info_type]
		for batch_info_dict in self._common_infos.modify_info_content():
			predict_kwargs = {
				"prompt": modify_prompt,
				ModifyPromptKeys.user_comment_key: user_response,
			}
			predict_kwargs.update(batch_info_dict)
			extract_info = await self._llm.apredict(**predict_kwargs)
			new_info_dict = parse_common_collected_info(
				extract_info=extract_info,
				info_keys=list(self._common_infos.required_infos.keys()),
			)
			print("modified: ", new_info_dict)
			self._common_infos.update_collected_info(collected_info_dict=new_info_dict)
