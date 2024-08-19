import json

from .base import REF_TYPE, RefInfoBase


class PaperInfo(RefInfoBase):
	def __init__(
		self,
		title: str,
		file_path: str,
		possessor: str,
	):
		self.title = title
		self.file_path = file_path
		self.possessor = possessor

	def dumps(self) -> str:
		info_dict = {
			REF_TYPE: PaperInfo.__name__,
			"title": self.title,
			"file_path": self.file_path,
			"possessor": self.possessor,
		}
		return json.dumps(info_dict)

	@classmethod
	def loads(cls, info_str: str):
		try:
			info_dict = json.loads(info_str)
			title = info_dict["title"]
			file_path = info_dict["file_path"]
			possessor = info_dict["possessor"]
			return cls(
				title=title,
				file_path=file_path,
				possessor=possessor,
			)
		except Exception:
			raise ValueError("Invalid paper info string.")
