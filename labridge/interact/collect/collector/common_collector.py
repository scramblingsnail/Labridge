import json
import copy

from llama_index.core.llms import LLM
from typing import List, Dict, Optional, Tuple

from labridge.interact.collect.types.info_base import CollectingInfoBase
from labridge.interact.collect.types.common_info import CollectingCommonInfo
from labridge.interact.prompt.collect.collect_info.prompt_keys import CollectPromptKeys
from labridge.interact.prompt.collect.modify_info.prompt_keys import ModifyPromptKeys

from labridge.interact.collect.manager.collect_manager import CollectManager
from labridge.interact.prompt.collect.collect_info.common_info import COLLECT_COMMON_INFO_PROMPT
from labridge.interact.prompt.collect.modify_info.common_info import MODIFY_COMMON_INFO_PROMPT


COLLECT_COMMON_INFO_QUERY = (
	"请补充完善如下信息, 您随时可以放弃本信息收集流程."
)


def parse_common_collected_info(extract_info: str, info_keys: List[str]) -> dict:
	try:
		chars = [char for char in extract_info]
		idx1 = chars.index("{")
		idx2 = chars.index("}")
		valid_info = "".join(chars[idx1:idx2+1])
		print(valid_info)
		items = json.loads(valid_info)
	except Exception:
		raise ValueError("Error: You should output a valid dictionary in JSON format !!!")

	output_info = dict()
	for key in items.keys():
		if key in info_keys and items[key] is not None:
			output_info[key] = items[key]
	return output_info


class CommonInfoCollector:
	r"""
	Collect CommonInfo from the user.
	refer to `..types.common_info.CollectingCommonInfo` for the detail of CommonInfo.

	Args:
		llm (LLM): The used LLM.
		required_infos (List[CollectingInfoBase]): The required infos.
	"""
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
		r"""
		Choose the CollectingCommonInfo from the required_infos.

		Args:
			required_infos (List[CollectingInfoBase]): The required infos.

		Returns:
			CollectingCommonInfo: All required CollectingCommonInfo are aggregated in a  CollectingCommonInfo.
				If no CollectingCommonInfo required, return None.
		"""
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
		r""" The information to be collected currently. """
		if self._common_infos is None:
			return None

		return self._common_infos.collecting_keys

	@property
	def collected_infos(self) -> Optional[Dict[str, str]]:
		r""" The Collected Common information. """
		if self._common_infos is None:
			return None

		return self._common_infos.collected_infos

	@property
	def collected(self):
		r""" Whether all Common information are collected or not. """
		if self._common_infos is None:
			return True

		return self._common_infos.collected

	@property
	def collecting_query(self) -> str:
		r""" This query will be sent to user to collect rest Common information. """
		query_to_user = f"{COLLECT_COMMON_INFO_QUERY}\n"
		for key in self.collecting_keys:
			query_to_user += f"\t{key}\n"
		return query_to_user

	def collect(self) -> bool:
		r"""
		Collect the Common information.

		Returns:
			bool: Whether the user aborts the collecting process.
		"""
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

		for batch_info_dict in self._common_infos.info_content():
			predict_kwargs = {
				"prompt": COLLECT_COMMON_INFO_PROMPT,
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
		r"""
		Asynchronously collect the Common information.

		Returns:
			bool: Whether the user aborts the collecting process.
		"""
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

		for batch_info_dict in self._common_infos.info_content():
			predict_kwargs = {
				"prompt": COLLECT_COMMON_INFO_PROMPT,
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
		r"""
		Modify the collected information according to the user's comment.

		Returns:
			Tuple[str, str]:
				- doing_modify: Whether the user thinks the collected information need modification.
				- abort: Whether the user aborts the collection process.
		"""
		if self._common_infos is None:
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
		r"""
		Asynchronously modify the collected information according to the user's comment.

		Returns:
			Tuple[str, str]:
				- doing_modify: Whether the user thinks the collected information need modification.
				- abort: Whether the user aborts the collection process.
		"""
		if self._common_infos is None:
			return False, False

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
		r"""
		Modify the collected information according to the user's comment.

		Args:
			user_response (str): The user's comment.

		Returns:
			None
		"""
		for batch_info_dict in self._common_infos.modify_info_content():
			predict_kwargs = {
				"prompt": MODIFY_COMMON_INFO_PROMPT,
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
		r"""
		Asynchronously modify the collected information according to the user's comment.

		Args:
			user_response (str): The user's comment.

		Returns:
			None
		"""
		for batch_info_dict in self._common_infos.modify_info_content():
			predict_kwargs = {
				"prompt": MODIFY_COMMON_INFO_PROMPT,
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
