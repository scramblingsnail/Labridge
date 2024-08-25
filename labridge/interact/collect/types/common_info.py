import json

from typing import List, Dict, Iterator

from .info_base import (
	CollectingInfoBase,
	CollectingBatchInfoBase,
	CollectingInfoType,
)

from ...prompt.collect.collect_info.prompt_keys import (
	CollectPromptKeys,
	DEFAULT_EXTRA_INFO,
)
from ...prompt.collect.modify_info.prompt_keys import ModifyPromptKeys


COMMON_COLLECT_BATCH_SIZE = 5


class CollectingCommonInfo(CollectingBatchInfoBase):
	r"""
	This class defines the common information to be collected from the user.
	The common information can be collected in batch mode.

	Args:
		info_name (str): The name of the information to be collected.
		info_description (str): The description of the information to be collected.
	"""
	def __init__(
		self,
		info_name: str,
		info_description: str,
	):
		self.info_dict = {
			CollectPromptKeys.required_infos_key: {info_name: info_description}
		}
		super().__init__(
			info_name=info_name,
			info_description=info_description,
			info_type=CollectingInfoType.COMMON,
		)

	def insert_info(self, info: CollectingInfoBase):
		r"""
		Insert a new CommonInfo to current one.

		Args:
			info (CollectingInfoBase): The new CollectingCommonInfo.

		Returns:
			None.
		"""
		self.info_dict[CollectPromptKeys.required_infos_key].update(
			{info.info_name: info.info_description}
		)

	def _collected(self) -> bool:
		r""" Whether all information is collected. """
		return len(self.collecting_keys) == 0

	def _required_infos(self) -> Dict[str, str]:
		r""" Return the required information names and descriptions. """
		return self.info_dict[CollectPromptKeys.required_infos_key]

	def update_collected_info(self, collected_info_dict: Dict[str, str]):
		r""" Update the collected information. """
		for key in collected_info_dict.keys():
			if key in self.required_infos:
				self._collected_infos[key] = collected_info_dict[key]

	def _collecting_keys(self) -> List[str]:
		r""" Return the information names to be collected currently. """
		collecting_keys = set(self.required_infos.keys()) - set(self._collected_infos.keys())
		return list(collecting_keys)

	def info_content(self) -> Iterator[Dict[str, str]]:
		r""" Yield a batch of information names and descriptions to the LLM for extraction """
		info_keys = self.collecting_keys
		info_num = len(info_keys)
		start = 0
		while start < info_num:
			batch_keys = info_keys[start: start + COMMON_COLLECT_BATCH_SIZE]
			start += COMMON_COLLECT_BATCH_SIZE
			batch_info = {key: self.required_infos[key] for key in batch_keys}
			yield {
				CollectPromptKeys.required_infos_key: json.dumps(batch_info),
				CollectPromptKeys.extra_info_key: DEFAULT_EXTRA_INFO,
			}

	def modify_info_content(self) -> Iterator[Dict[str, str]]:
		r""" Yield a batch of information names, descriptions and collected content to the LLM for modification. """
		info_keys = list(self.collected_infos.keys())
		info_num = len(info_keys)
		start = 0
		while start < info_num:
			batch_keys = info_keys[start: start + COMMON_COLLECT_BATCH_SIZE]
			start += COMMON_COLLECT_BATCH_SIZE
			batch_info = {key: self.required_infos[key] for key in batch_keys}
			batch_collected_info = {key: self.collected_infos[key] for key in batch_keys}
			yield {
				ModifyPromptKeys.required_infos_key: json.dumps(batch_info),
				ModifyPromptKeys.collected_infos_key: json.dumps(batch_collected_info),
				ModifyPromptKeys.extra_info_key: DEFAULT_EXTRA_INFO,
			}
