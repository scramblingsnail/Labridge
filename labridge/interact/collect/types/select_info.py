import json

from .info_base import (
	CollectingInfoBase,
	CollectingInfoType,
)

from labridge.interact.prompt.collect.collect_info.prompt_keys import CollectPromptKeys
from labridge.interact.prompt.collect.modify_info.prompt_keys import ModifyPromptKeys


from typing import List, Dict, Iterator, Tuple


SELECT_CHOICE_BATCH_SIZE = 8

SELECT_MIN_SCORE = 6


class CollectingSelectInfo(CollectingInfoBase):
	r"""
	This class defines the select information to be collected from the user.
	The select information should be selected between several given choices.

	Args:
		info_name (str): The name of the information to be collected.
		info_description (str): The description of the information to be collected.
		choices (Dict[str, str]):
			The given choices.

			- key (str): The choice.
			- value (str): The description of the choice.
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
		r""" Whether all information is collected. """
		return self.info_name in self._collected_infos.keys()

	def update_collected_info(self, collected_info_dict: Dict[str, str]):
		r""" Update the collected information. """
		if self.info_name in collected_info_dict:
			self._collected_infos[self.info_name] = collected_info_dict[self.info_name]

	def _required_infos(self) -> Dict[str, str]:
		r""" Return the required information names and descriptions. """
		return {self.info_name: self.info_description}

	def _collecting_keys(self) -> List[str]:
		r""" Return the information names to be collected currently. """
		if self.collected:
			return []
		return [self.info_name]

	@property
	def candidates(self) -> List[str]:
		r""" Get the candidates """
		return list(self._choices.keys())

	def _extra_info_format(self, choice_keys: List[str]) -> str:
		r""" The prompt format for selecting. """
		contents = []
		for idx, key in enumerate(choice_keys):
			content = f"Paragraph {idx + 1}\n"
			content += f"Name: {key}\nDescription: {self._choices[key]}".strip()
			contents.append(content)
		choices_str = "\n\n".join(contents)
		return choices_str

	def info_content(self) -> Iterator[Tuple[Dict[str, str], List[str]]]:
		r""" Yield the information name, description and corresponding choices to the LLM for selection. """
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
		r""" Yield the information name, description, collected content and corresponding choices to the LLM for modification. """
		required_infos_str = json.dumps({self.info_name: self.info_description})
		candidates = self.candidates
		for idx in range(0, len(candidates), SELECT_CHOICE_BATCH_SIZE):
			extra_info = self._extra_info_format(choice_keys=candidates[idx: idx + SELECT_CHOICE_BATCH_SIZE])
			yield {
				CollectPromptKeys.required_infos_key: required_infos_str,
				ModifyPromptKeys.collected_infos_key: json.dumps(self.collected_infos),
				CollectPromptKeys.extra_info_key: extra_info,
			}, candidates[idx: idx + SELECT_CHOICE_BATCH_SIZE]
