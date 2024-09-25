from abc import abstractmethod

REF_TYPE = "ref_type"
REF_INFO_FILE_PATH_KEY = "ref_file_path"
REF_INFO_FILE_SIZE_KEY = "ref_file_size"


class RefInfoBase:
	r"""
	This is the base class for reference information.
	"""
	def __init__(self, ref_file_path: str = None):
		self.ref_file_path = ref_file_path

	@abstractmethod
	def dumps(self):
		r""" Dump an object of the class to a string in JSON format. """

	@classmethod
	@abstractmethod
	def loads(cls, info_str):
		r""" Load an object of the class from a string in JSON format. """
