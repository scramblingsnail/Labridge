import json
import fsspec

from typing import Dict, List, Union
from pathlib import Path

from labridge.accounts.users import AccountManager


SUPER_USER_IDS_PERSIS_PATH = "storage/accounts/instruments_super_user_ids.json"


class InstrumentSuperUserManager(object):
	r"""
	This is the account manager of super-users.

	Each set of super-users are related to a specific scientific instrument.
	These super-users own full authority to their instruments, and are responsible for the instrument management such as
	updating instruction manual, adding a new super-user, etc.

	The accounts of super-users are stored as a dictionary as follows in a json format.
	`{instrument_id: [super_user_ids, ]}`
	"""
	def __init__(self):
		root = Path(__file__)
		for idx in range(3):
			root = root.parent
		self.root = root
		self.super_user_ids_path = str(root / SUPER_USER_IDS_PERSIS_PATH)
		self.fs = fsspec.filesystem("file")
		dir_path = str(Path(self.super_user_ids_path).parent)
		if not self.fs.exists(dir_path):
			self.fs.makedirs(dir_path)

	def _get_user_ids_dict(self) -> Dict[str, List[str]]:
		r""" Get the super-user accounts dictionary. """
		if not self.fs.exists(self.super_user_ids_path):
			return {}
		with self.fs.open(self.super_user_ids_path, "rb") as f:
			super_user_ids = json.load(f)
		return super_user_ids

	def get_super_users(self, instrument_id: str) -> List[str]:
		r""" Get the super-users of a specific instrument. """
		return list(self._get_user_ids_dict()[instrument_id])

	def is_super_user(self, user_id: str, instrument_id: str) -> bool:
		r""" Judge whether a user is the super-user of a instrument. """
		super_user_list = self.get_super_users(instrument_id=instrument_id)
		return user_id in super_user_list

	@staticmethod
	def check_users(user_id: Union[str, List[str]]):
		r""" Check whether all given users have registered."""
		user_manager = AccountManager()
		if not isinstance(user_id, list):
			user_id = [user_id]

		for user in user_id:
			user_manager.check_valid_user(user_id=user)

	def add_super_user(self, user_id: str, instrument_id: str):
		r""" Add a new super-user for the instrument. """
		super_user_ids = self._get_user_ids_dict()
		self.check_users(user_id=user_id)

		if instrument_id not in super_user_ids.keys():
			raise ValueError(f"The instrument {instrument_id} is not registered yet.")

		super_user_ids[instrument_id].append(user_id)
		with self.fs.open(self.super_user_ids_path, "w") as f:
			f.write(json.dumps(super_user_ids))

	def delete_super_user(self, user_id: str, instrument_id: str):
		r""" Delete a super-user of the instrument. """
		super_user_ids = self._get_user_ids_dict()
		if instrument_id not in super_user_ids.keys():
			raise ValueError(f"The instrument {instrument_id} is not registered yet.")
		super_user_ids[instrument_id].remove(user_id)
		with self.fs.open(self.super_user_ids_path, "w") as f:
			f.write(json.dumps(super_user_ids))

	def add_instrument(self, instrument_id: str, super_users: List[str]):
		r""" Add a new instrument along with its super-users. """
		super_user_ids = self._get_user_ids_dict()
		if instrument_id in super_user_ids.keys():
			raise ValueError(f"The instrument {instrument_id} already exists.")

		self.check_users(user_id=super_users)
		super_user_ids[instrument_id] = super_users
		with self.fs.open(self.super_user_ids_path, "w") as f:
			f.write(json.dumps(super_user_ids))
