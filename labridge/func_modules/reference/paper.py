import json

from .base import REF_TYPE, RefInfoBase, REF_INFO_FILE_PATH_KEY


class PaperInfo(RefInfoBase):
	r"""
	This class contains the information of a paper, including:

	Args:
		title (str): The title of the paper.
		file_path (str): The file path of the paper.
		possessor (str): The user that possesses the paper.
	"""
	def __init__(
		self,
		title: str,
		file_path: str,
		possessor: str,
		doi: str = None,
	):
		self.title = title
		self.possessor = possessor
		self.doi = doi
		super().__init__(ref_file_path=file_path)

	def dumps(self) -> str:
		r""" Dump to a string in JSON format. """
		info_dict = {
			REF_TYPE: PaperInfo.__name__,
			"title": self.title,
			REF_INFO_FILE_PATH_KEY: self.ref_file_path,
			"possessor": self.possessor,
			"doi": self.doi,
		}
		return json.dumps(info_dict)

	@classmethod
	def loads(cls, info_str: str):
		r""" Load from a string in JSON format. """
		try:
			info_dict = json.loads(info_str)
			title = info_dict["title"]
			ref_file_path = info_dict[REF_INFO_FILE_PATH_KEY]
			possessor = info_dict["possessor"]
			doi = info_dict["doi"]
			return cls(
				title=title,
				file_path=ref_file_path,
				possessor=possessor,
				doi=doi,
			)
		except Exception:
			raise ValueError("Invalid paper info string.")
