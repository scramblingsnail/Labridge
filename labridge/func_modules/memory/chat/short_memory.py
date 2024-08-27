import fsspec
import datetime

from llama_index.core.storage.chat_store.simple_chat_store import SimpleChatStore
from llama_index.core.base.llms.types import ChatMessage

from labridge.common.utils.time import get_time, str_to_date, str_to_time, str_to_datetime

from pathlib import Path
from typing import List, Optional


SHORT_MEMORY_PERSIST_DIR = "storage/short_memory"


class ShortMemoryManager(object):
	r"""
	This class manage the short-term chat memories between the agent and users.

	Attributes:
		_root (Optional[str]): The project root.
		_valid_delta_days (Optional[int]): Only valid chat histories will be loaded.
		_valid_delta_hours (Optional[int]): Same as above.
		_valid_delta_minutes (Optional[int]): Same as above.
	"""
	_root: Optional[str] = None
	_valid_delta_days: Optional[int] = 0,
	_valid_delta_hours: Optional[int] = 2,
	_valid_delta_minutes: Optional[int] = 30,

	@property
	def root(self) -> str:
		r""" Return the project root """
		if self._root is None:
			root_dir = Path(__file__)
			for idx in range(4):
				root_dir = root_dir.parent
			self._root = str(root_dir)
		return self._root

	@property
	def valid_delta_time(self) -> datetime.timedelta:
		r""" Return the valid time delta. """
		return datetime.timedelta(
			days=self._valid_delta_days,
			hours=self._valid_delta_hours,
			minutes=self._valid_delta_minutes,
		)

	@staticmethod
	def _pack_time_key(date_str: str, time_str: str) -> str:
		return f"{date_str} {time_str}"

	@staticmethod
	def _unpack_time_key(time_key: str) -> datetime.datetime:
		date_str, time_str = time_key.split()
		last_datetime = str_to_datetime(date_str=date_str, time_str=time_str)
		return last_datetime

	def load_memory(self, user_id: str) -> Optional[List[ChatMessage]]:
		r"""
		Only chat messages within the valid time delta will be loaded.

		Args:
			user_id (str): The user_id of a lab member.

		Returns:
			The loaded short memory:
				If the short memory storage does not exist or the datetime of the short memory is invalid, return None.
		"""
		persist_path = Path(self.root) / f"{SHORT_MEMORY_PERSIST_DIR}/{user_id}.json"
		fs = fsspec.filesystem("file")
		if not fs.exists(persist_path):
			return None

		chat_store = SimpleChatStore.from_persist_path()
		keys = chat_store.get_keys()
		if len(keys) < 1:
			fs.rm(persist_path)
			return None
		time_key = chat_store.get_keys()[0]
		last_datetime = self._unpack_time_key(time_key=time_key)
		now = datetime.datetime.now()
		if last_datetime + self.valid_delta_time < now:
			return None
		return chat_store.store[time_key]

	def save_memory(self, user_id: str, chat_history: List[ChatMessage]):
		r"""
		Persist the short-term memory for the user's next chat request.

		Args:
			user_id (str): The user id of a Lab member.
			chat_history (List[ChatMessage]): Current chat history between the user and agent.
		"""
		date, h_m_s = get_time()
		time_key = self._pack_time_key(date_str=date, time_str=h_m_s)
		store_dict = {
			time_key: chat_history,
		}
		chat_store = SimpleChatStore(store=store_dict)
		persist_path = Path(self.root) / f"{SHORT_MEMORY_PERSIST_DIR}/{user_id}.json"
		persist_path = str(persist_path)
		chat_store.persist(persist_path=persist_path)
