import pymupdf

from abc import abstractmethod
from pathlib import Path
from typing import Union, Tuple, Dict, List, Sequence, Optional
from llama_index.core.schema import Document



CONTENT_TYPE_NAME = "Content type"

# Content names:
# Note: no '_' is allowed in a Content name.
ABSTRACT = "Abstract"
MAINTEXT = "MainText"
REFERENCES = "References"
METHODS = "Methods"

# Categories:
MetadataContents = (
	ABSTRACT,
)

ChunkContents = (
	MAINTEXT,
	METHODS
)

ExtraContents = (
	REFERENCES
)



def match_separators(text: str, separators: Sequence[str], tolerance: int):
	tolerance = max(tolerance, 1)

	text = text.replace("\n", "")
	for sep in separators:
		for start in range(tolerance):
			if text[start: start + len(sep)].upper() == sep.upper():
				return True
	return False


def get_sep_idx(text: str, separators: List[Tuple[str]], tolerance: int):
	sep_idx = -1
	for idx, each_separators in enumerate(separators):
		if match_separators(text, each_separators, tolerance):
			sep_idx = idx
			break
	return sep_idx


class BasePaperParser:
	r"""
	This is the base paper parser.
	The Parser separates a paper into subcomponents according to several separators.

	Args:
		separators (List[Tuple[str]]): Each tuple includes the separators that separate two components.
		content_names (Dict[int, Tuple[str]): Key: component index; Value: component name candidates.
		separator_tolerance (int): The tolerance of mismatch chars.
	"""
	def __init__(
		self,
		separators: List[Tuple[str]],
		content_names: Dict[int, Tuple[str]],
		separator_tolerance: int = 3
	):
		self.separators = separators
		self.content_names = content_names
		self.separator_tolerance = separator_tolerance

	@abstractmethod
	def parse_title(self, file_path: Union[str, Path]) -> str:
		...

	def to_documents(
		self,
		parsed_components: List[str],
		extra_info: Dict[str, str],
	) -> List[Document]:
		r"""
		Transform the parsed components to Documents.

		Args:
			parsed_components (List[str]): The separated component strings.
			extra_info (Dict[str, str]): The extra information will be recorded in the Document's metadata.

		Returns:
			List[Document]: The parsed Documents.
		"""
		component_names = self.content_names[len(parsed_components)]
		documents = []

		# merge texts with the same name.
		merged_component_names = []
		merged_components = []
		for idx, name in enumerate(component_names):
			if name not in merged_component_names:
				merged_component_names.append(name)
				merged_components.append(parsed_components[idx])
			else:
				name_idx = merged_component_names.index(name)
				merged_components[name_idx] += parsed_components[idx]

		for idx, component in enumerate(merged_components):
			doc_info = {CONTENT_TYPE_NAME: merged_component_names[idx]}
			doc_info.update(extra_info)
			doc = Document(text=merged_components[idx], extra_info=doc_info)
			documents.append(doc)
		return documents

	def parse_paper(self, file_path: Union[str, Path]) -> List[Document]:
		r"""
		Split the article into main text, methods, extra info (references, extended data.) according to specific separators.
		For example, separators for Nature are:

		Example:
			```python
			>>> [
			... 	("Online content", ),
			... 	("Methods", ),
			... 	("Data availability", "Code availability", "References")
			... ]
			```

		Args:
			file_path (Union[str, Path]): The paper path.

		Returns:
			Tuple[List, Optional[str]]:

				- The separated paper text (List[str]): For example: [Main text, References 1, Methods, References 2]
				- The title (Optional[str]): Might be None if PyMuPDF failed to extract the doc toc. In that case you may
				need to search for LLM's help to extract it.
		"""
		if not isinstance(file_path, str) and not isinstance(file_path, Path):
			raise TypeError("file_path must be a string or Path.")

		separators = self.separators
		doc = pymupdf.open(file_path)
		pages = [page.get_textpage() for page in doc]

		text_blocks = []
		sep_p = 0
		components = []
		text_in_block = 4
		for idx, text_page in enumerate(pages):
			page_blocks = text_page.extractBLOCKS()
			if idx == 0:
				page_blocks.pop(0)
			for each_block in page_blocks:
				sep_idx = get_sep_idx(each_block[text_in_block], separators, self.separator_tolerance)
				if sep_p < len(separators) and sep_idx >= sep_p:
					text_list = [block[text_in_block] for block in text_blocks]
					text = ''.join(text_list)
					components.append(text)
					sep_p = sep_idx + 1
					text_blocks = []
				text_blocks.append(each_block)
		else:
			text_list = [block[text_in_block] for block in text_blocks]
			text = ''.join(text_list)
			components.append(text)

		extra_info = {
			"total_pages": len(doc),
			"file_path": str(file_path)
		}

		documents = self.to_documents(parsed_components=components, extra_info=extra_info)
		return documents
