import pymupdf

from pathlib import Path
from typing import Union, Tuple, Optional, List, Dict
from llama_index.core.schema import Document

from .base import BasePaperParser, CONTENT_TYPE_NAME
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
	def __init__(self,
				 separators: List[Tuple[str]] = None,
				 content_names: Dict[int, Tuple[str]] = None,
				 separator_tolerance: int = 3):
		separators = separators or IEEE_SEPARATORS
		content_names = content_names or IEEE_CONTENT_NAMES
		super().__init__(separators, content_names, separator_tolerance)

	def parse_title(self, file_path: Union[str, Path]) -> str:
		r""" Suggest you to use LLM to extract title and other information. """
		doc = pymupdf.open(file_path)
		page = doc[0].get_textpage()

		page_blocks = page.extractBLOCKS()
		title = page_blocks[0][4].replace("\n", "")
		return title
