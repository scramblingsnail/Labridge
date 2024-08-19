import json

from .info_base import (
	CollectingInfoBase,
	CollectingInfoType,
)

from ...prompt.collect.collect_info.prompt_keys import CollectPromptKeys
from ...prompt.collect.modify_info.prompt_keys import ModifyPromptKeys


from typing import List, Dict, Iterator, Tuple



SELECT_CHOICE_BATCH_SIZE = 8

SELECT_MIN_SCORE = 6


class CollectingSelectInfo(CollectingInfoBase):
	r"""

	"""
	def __init__(
		self,
		info_name: str,
		info_description: str,
		choices: Dict[str, str],
	):
		self._choices = choices
		super().__init__(
			info_name=info_name,
			info_description=info_description,
			info_type=CollectingInfoType.SELECT,
			batch_mode=False,
		)

	def _collected(self) -> bool:
		return self.info_name in self._collected_infos.keys()

	def update_collected_info(self, collected_info_dict: Dict[str, str]):
		if self.info_name in collected_info_dict:
			self._collected_infos[self.info_name] = collected_info_dict[self.info_name]

	def _required_infos(self) -> Dict[str, str]:
		return {self.info_name: self.info_description}

	def _collecting_keys(self) -> List[str]:
		if self.collected:
			return []
		return [self.info_name]

	@property
	def candidates(self) -> List[str]:
		return list(self._choices.keys())

	def _extra_info_format(self, choice_keys: List[str]) -> str:
		contents = []
		for idx, key in enumerate(choice_keys):
			content = f"Paragraph {idx + 1}\n"
			content += f"Name: {key}\nDescription: {self._choices[key]}".strip()
			contents.append(content)
		choices_str = "\n\n".join(contents)
		return choices_str

	def info_content(self) -> Iterator[Tuple[Dict[str, str], List[str]]]:
		required_infos_str = json.dumps({self.info_name: self.info_description})
		candidates = self.candidates
		if not self.collected:
			for idx in range(0, len(candidates), SELECT_CHOICE_BATCH_SIZE):
				extra_info = self._extra_info_format(choice_keys=candidates[idx: idx + SELECT_CHOICE_BATCH_SIZE])
				yield {
					CollectPromptKeys.required_infos_key: required_infos_str,
					CollectPromptKeys.extra_info_key: extra_info,
				}, candidates[idx: idx + SELECT_CHOICE_BATCH_SIZE]

	def modify_info_content(self) -> Iterator[Tuple[Dict[str, str], List[str]]]:
		required_infos_str = json.dumps({self.info_name: self.info_description})
		candidates = self.candidates
		for idx in range(0, len(candidates), SELECT_CHOICE_BATCH_SIZE):
			extra_info = self._extra_info_format(choice_keys=candidates[idx: idx + SELECT_CHOICE_BATCH_SIZE])
			yield {
				CollectPromptKeys.required_infos_key: required_infos_str,
				ModifyPromptKeys.collected_infos_key: json.dumps(self.collected_infos),
				CollectPromptKeys.extra_info_key: extra_info,
			}, candidates[idx: idx + SELECT_CHOICE_BATCH_SIZE]