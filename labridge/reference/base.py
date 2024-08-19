from abc import abstractmethod

REF_TYPE = "ref_type"


class RefInfoBase:

	@abstractmethod
	def dumps(self):
		r""" Dump an object of the class to a string. """

	@classmethod
	@abstractmethod
	def loads(cls, info_str):
		r""" Load an object of the class from a string. """