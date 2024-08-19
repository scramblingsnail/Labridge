from enum import Enum
from abc import abstractmethod
from typing import List, Dict


class CollectingInfoType(Enum):
	SELECT = "select"
	COMMON = "common"


class CollectingInfoBase:
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
		r"""  """

	@abstractmethod
	def _required_infos(self) -> Dict[str, str]:
		r""" required infos """

	@abstractmethod
	def update_collected_info(self, collected_info):
		r""" update self._collected_infos """

	@property
	def required_infos(self) -> Dict[str, str]:
		return self._required_infos()

	@property
	def batch_mode(self) -> bool:
		return self._batch_mode

	@abstractmethod
	def _collected(self) -> bool:
		r""" Whether the collecting process ends. """

	@property
	def collected(self) -> bool:
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
		return self._collecting_keys()


class CollectingBatchInfoBase(CollectingInfoBase):
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
