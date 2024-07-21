import pymupdf

from typing import Union, List
from pathlib import Path
from llama_index.core.schema import Document

from .base import CONTENT_TYPE_NAME


class DefaultPaperParser:
	def parse_paper(self, file_path: Union[str, Path]) -> List[Document]:
		doc = pymupdf.open(file_path)
		pages = [page.get_text().encode("utf-8") for page in doc]
		paper_text = ''.join([text for text in pages])

		extra_info = {
			"total_pages": len(doc),
			"file_path": str(file_path),
			CONTENT_TYPE_NAME: "MainText"
		}
		doc = Document(text=paper_text, extra_info=extra_info)
		return [doc,]
