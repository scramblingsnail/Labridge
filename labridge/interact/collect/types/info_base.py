from enum import Enum
from abc import abstractmethod
from typing import List, Dict


class CollectingInfoType(Enum):
	SELECT = "select"
	COMMON = "common"


class CollectingInfoBase:
	r"""
	This is the base class for the CollectingInfo.

	Args:
		info_name (str): The information name.
		info_description (str): The information description.
		info_type (CollectingInfoType): The information type.
		batch_mode (bool): Whether the information can be collected in a batch mode.
	"""
	def __init__(
		self,
		info_name: str,
		info_description: str,
		info_type: CollectingInfoType,
		batch_mode: bool,
	):
		self.info_name = info_name
		self.info_description = info_description
		self.info_type = info_type
		self._batch_mode = batch_mode
		self._collect_finish = False
		self._collected_infos = {}

	@abstractmethod
	def info_content(self) -> Dict[str, str]:
		r""" Yield the information to the LLM for extraction. """

	@abstractmethod
	def _required_infos(self) -> Dict[str, str]:
		r""" Required infos """

	@abstractmethod
	def update_collected_info(self, collected_info):
		r""" Update self._collected_infos """

	@property
	def required_infos(self) -> Dict[str, str]:
		r""" Required infos """
		return self._required_infos()

	@property
	def batch_mode(self) -> bool:
		return self._batch_mode

	@abstractmethod
	def _collected(self) -> bool:
		r""" Whether the collecting process ends. """

	@property
	def collected(self) -> bool:
		r""" Whether all required infos are collected. """
		return self._collected()

	@property
	def collected_infos(self) -> dict:
		r""" Return the collected info . """
		return self._collected_infos

	@abstractmethod
	def _collecting_keys(self) -> List[str]:
		r""" The keys in collecting. """

	@property
	def collecting_keys(self) -> List[str]:
		r""" The collecting information names. """
		return self._collecting_keys()


class CollectingBatchInfoBase(CollectingInfoBase):
	r"""
	The CollectingInfo which can be collected in a batch mode.
	"""
	def __init__(
		self,
		info_name: str,
		info_description: str,
		info_type: CollectingInfoType,
	):
		super().__init__(
			info_name=info_name,
			info_description=info_description,
			info_type=info_type,
			batch_mode=True,
		)

	@abstractmethod
	def insert_info(self, **kwargs):
		r""" insert info """
