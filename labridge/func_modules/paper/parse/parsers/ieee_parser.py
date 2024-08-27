import pymupdf

from pathlib import Path
from typing import Union, Tuple, List, Dict

from .base import BasePaperParser
from .base import (
	ABSTRACT,
	MAINTEXT,
	REFERENCES
)


IEEE_SEPARATORS = [
	("Introduction", ),
	("References",)
]

# Key: component num; Value: component names
IEEE_CONTENT_NAMES = {
	1: (MAINTEXT, ),
	2: (ABSTRACT, MAINTEXT),
	3: (ABSTRACT, MAINTEXT, REFERENCES)
}



class IEEEPaperParser(BasePaperParser):
	r"""
	Parse the paper according to the IEEE template.

	Args:
		separators (List[Tuple[str]]): Each tuple includes the separators that separate two components.
			Defaults to `IEEE_SEPARATORS`.
		content_names (Dict[int, Tuple[str]): Key: component index; Value: component name candidates.
			Defaults to `IEEE_CONTENT_NAMES`.
		separator_tolerance (int): The tolerance of mismatch chars.
	"""
	def __init__(
		self,
		separators: List[Tuple[str]] = None,
		content_names: Dict[int, Tuple[str]] = None,
		separator_tolerance: int = 3
	):
		separators = separators or IEEE_SEPARATORS
		content_names = content_names or IEEE_CONTENT_NAMES
		super().__init__(separators, content_names, separator_tolerance)

	def parse_title(self, file_path: Union[str, Path]) -> str:
		r""" Suggest to use LLM to extract title and other information. """
		doc = pymupdf.open(file_path)
		page = doc[0].get_textpage()

		page_blocks = page.extractBLOCKS()
		title = page_blocks[0][4].replace("\n", "")
		return title
