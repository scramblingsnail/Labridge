import json

from typing import List
from .base import REF_TYPE, RefInfoBase


class ExperimentLogRefInfo(RefInfoBase):
	r"""
	This class contains the information of a paper, including:

	Args:
		date_time (str): The title of the paper.
		attachment_path (str): The file path of the paper.
		possessor (str): The user that possesses the paper.
		experiment_name (str): The experiment name of the log.
	"""
	def __init__(
		self,
		date_time: str,
		log_str: str,
		experiment_name: str,
		attachment_path: str = None,
	):
		self.date_time = date_time
		self.log_str = log_str
		self.attachment_path = attachment_path
		self.experiment_name = experiment_name

	def dumps(self) -> str:
		r""" Dump to a string in JSON format. """
		info_dict = {
			REF_TYPE: ExperimentLogRefInfo.__name__,
			"date_time": self.date_time,
			"log_str": self.log_str,
			"attachment_path": self.attachment_path,
			"experiment_name": self.experiment_name,
		}
		return json.dumps(info_dict)

	@classmethod
	def loads(cls, info_str: str):
		r""" Load from a string in JSON format. """
		try:
			info_dict = json.loads(info_str)
			date_time = info_dict["date_time"]
			log_str = info_dict["log_str"]
			attachment_path = info_dict["attachment_path"]
			experiment_name = info_dict["experiment_name"]
			return cls(
				date_time=date_time,
				attachment_path=attachment_path,
				log_str=log_str,
				experiment_name=experiment_name,
			)
		except Exception:
			raise ValueError("Invalid experiment log info string.")
