import pymupdf

from pathlib import Path
from typing import Union, Tuple, List, Dict

from .base import BasePaperParser

from .base import (
	MAINTEXT,
	REFERENCES,
	METHODS
)


NATURE_SEPARATORS = [
	("Online content", ),
	("Methods", ),
	("Data availability", "Code availability", "References")
]

NATURE_CONTENT_NAMES = {
	1: (MAINTEXT, ),
	2: (MAINTEXT, REFERENCES),
	3: (MAINTEXT, METHODS, REFERENCES),
	4: (MAINTEXT, REFERENCES, METHODS, REFERENCES)
}


class NaturePaperParser(BasePaperParser):
	r"""
	Parse the paper according to the Nature template.

	Args:
		separators (List[Tuple[str]]): Each tuple includes the separators that separate two components.
			Defaults to `NATURE_SEPARATORS`.
		content_names (Dict[int, Tuple[str]): Key: component index; Value: component name candidates.
			Defaults to `NATURE_CONTENT_NAMES`.
		separator_tolerance (int): The tolerance of mismatch chars.
	"""
	def __init__(self,
				 separators: List[Tuple[str]] = None,
				 content_names: Dict[int, Tuple[str]] = None,
				 separator_tolerance: int = 3):
		separators = separators or NATURE_SEPARATORS
		content_names = content_names or NATURE_CONTENT_NAMES
		super().__init__(separators, content_names, separator_tolerance)

	def parse_title(self, file_path: Union[str, Path]) -> str:
		r""" Suggest to use LLM to extract title and other information. """
		doc = pymupdf.open(file_path)
		toc = doc.get_toc()
		title = None
		try:
			while isinstance(toc[0], list):
				toc = toc[0]
				title = toc[1]
		except IndexError:
			print(f">>> PyMupdf failed to get toc from {file_path}")
		return title
