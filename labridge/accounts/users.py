import json
import fsspec

from pathlib import Path
from typing import Dict, List, Optional


USER_IDS_PERSIS_PATH = "storage/accounts/user_ids.json"
CHAT_GROUP_IDS_PERSIST_PATH = "storage/accounts/chat_group_ids.json"



class AccountManager(object):
	def __init__(self):
		root = Path(__file__)
		for idx in range(3):
			root = root.parent
		self.root = root
		self.user_ids_path = str(root / USER_IDS_PERSIS_PATH)
		self.chat_group_ids_path = str(root / CHAT_GROUP_IDS_PERSIST_PATH)
		self.fs = fsspec.filesystem("file")
		dir_path = str(Path(self.user_ids_path).parent)
		if not self.fs.exists(dir_path):
			self.fs.makedirs(dir_path)

	def _get_user_ids_dict(self) -> Dict[str, str]:
		if not self.fs.exists(self.user_ids_path):
			return {}
		with self.fs.open(self.user_ids_path, "rb") as f:
			user_ids = json.load(f)
		return user_ids

	def _get_chat_group_ids_dict(self) -> Dict[str, List[str]]:
		if not self.fs.exists(self.chat_group_ids_path):
			return {}
		with self.fs.open(self.chat_group_ids_path, "rb") as f:
			chat_group_ids = json.load(f)
		return chat_group_ids

	def get_users(self) -> List[str]:
		return list(self._get_user_ids_dict().keys())

	def get_chat_groups(self) -> List[str]:
		return list(self._get_chat_group_ids_dict().keys())

	def is_valid_user(self, user_id: str):
		user_list = self.get_users()
		if user_id not in user_list:
			raise ValueError(f"The user {user_id} is not registered.")

	def is_valid_chat_group(self, chat_group_id: str):
		chat_group_list = self.get_chat_groups()
		if chat_group_id not in chat_group_list:
			raise ValueError(f"The chat group {chat_group_id} is not registered.")

	def add_user(self, user_id: str, password: str):
		user_ids = self._get_user_ids_dict()

		if user_id not in user_ids:
			user_ids[user_id] = password
			with self.fs.open(self.user_ids_path, "w") as f:
				f.write(json.dumps(user_ids))

	def add_chat_group(self, chat_group_id: str, user_list: List[str]) -> Optional[str]:
		for user_id in user_list:
			try:
				self.is_valid_user(user_id)
			except ValueError as e:
				return f"Error: {e!s}"

		chat_group_ids = self._get_chat_group_ids_dict()

		if chat_group_id not in chat_group_ids:
			chat_group_ids[chat_group_id] = user_list
			with self.fs.open(self.chat_group_ids_path, "w") as f:
				f.write(json.dumps(chat_group_ids))
			return None

	def update_chat_group_members(self, chat_group_id: str, new_user_list: List[str]) -> Optional[str]:
		for user_id in new_user_list:
			try:
				self.is_valid_user(user_id)
			except ValueError as e:
				return f"Error: {e!s}"

		chat_group_ids = self._get_chat_group_ids_dict()
		chat_group_ids[chat_group_id] = new_user_list
		with self.fs.open(self.chat_group_ids_path, "w") as f:
			f.write(json.dumps(chat_group_ids))
		return None
