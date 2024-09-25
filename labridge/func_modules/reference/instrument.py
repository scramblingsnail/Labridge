import json

from typing import List

from .base import REF_TYPE, RefInfoBase


class InstrumentInfo(RefInfoBase):
	r"""
	This class contains the information of an instrument, including:

	Args:
		instrument_id (str): The name of the instrument.
		super_users (List[str]): The super-users of the instrument.
	"""
	def __init__(
		self,
		instrument_id: str,
		super_users: List[str],
	):
		self.instrument_id = instrument_id
		self.super_users = super_users
		super().__init__()

	def dumps(self) -> str:
		r""" Dump to a string in JSON format. """
		info_dict = {
			REF_TYPE: InstrumentInfo.__name__,
			"instrument_id": self.instrument_id,
			"super_users": self.super_users,
		}
		return json.dumps(info_dict)

	@classmethod
	def loads(
		cls,
		info_str: str,
	):
		r""" Load from a string in JSON format. """
		try:
			info_dict = json.loads(info_str)
			instrument_id = info_dict["instrument_id"]
			super_users = info_dict["super_users"]
			return cls(
				instrument_id=instrument_id,
				super_users=super_users,
			)
		except Exception:
			raise ValueError("Invalid Instrument info string.")

