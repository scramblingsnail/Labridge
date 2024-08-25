from llama_index.core.settings import llm_from_settings_or_context
from llama_index.core.llms import LLM
from llama_index.core import ServiceContext, Settings

from llama_index.core.indices.keyword_table import KeywordTableIndex

from enum import Enum
from pathlib import Path
from typing import Union


class PaperSource(str, Enum):
	DEFAULT = "Default"
	NATURE = "Nature"
	IEEE = "IEEE"


class PaperSourceAnalyzer:
	r"""
	This class analyze the source of the paper, such as 'Nature', 'IEEE'.

	In default, the source analysis bases on keyword occurrence count.
	Also, LLM can be used to help analyzing the source.

	Args:
		llm (LLM): The used LLM.
		service_context (ServiceContext): The service context.
		keyword_count_threshold (int): A PaperSource is selected as a candidate
			only if its corresponding keyword occurrence count exceed this threshold.
	"""
	def __init__(
		self,
		llm: LLM = None,
		service_context: ServiceContext = None,
		keyword_count_threshold: int = 10,
	):
		self.llm = llm or llm_from_settings_or_context(Settings, service_context)
		self.keyword_count_threshold = keyword_count_threshold

	def reader_analyze(self, paper_path: Union[Path, str]) -> PaperSource:
		"""
		Analyze the paper source using a structured pdf reader.

		Args:
			paper_path (Union[Path, str]): The paper path.

		Returns:
			PaperSource: The paper source.
		"""
		import PyPDF2

		with open(paper_path, 'rb') as file:
			fileReader = PyPDF2.PdfReader(file)
			file_info = fileReader.trailer['/Info']

		source = None
		if '/Subject' in file_info.keys():
			src_string = file_info['/Subject']
			if len(src_string) >= len(PaperSource.NATURE):
				source = PaperSource.IEEE
				for start in range(len(src_string) - len(PaperSource.NATURE) + 1):
					if src_string[start: start + len(PaperSource.NATURE)].upper() == PaperSource.NATURE.upper():
						source = PaperSource.NATURE
		return source

	def llm_analyze(self, paper_path: Union[Path, str]) -> PaperSource:
		""" TODO: using llm. """
		return PaperSource.DEFAULT

	def keyword_analyze(self, paper_path: Union[Path, str]) -> PaperSource:
		r"""
		Analyze the paper source based on keyword occurrence count.

		Args:
			paper_path (Union[Path, str]): The paper path.

		Returns:
			PaperSource: The analyzed paper source.
		"""
		import pymupdf
		import re

		doc = pymupdf.open(paper_path)
		pages = [page.get_text() for page in doc]

		""" Searching in the text."""
		source = None
		count = 0
		for page_text in pages:
			for t in re.findall(r"\w+", page_text):
				if t.strip().upper() == PaperSource.NATURE.upper():
					count += 1
		if count > self.keyword_count_threshold:
			source = PaperSource.NATURE
		else:
			source = PaperSource.IEEE
		return source

	def analyze_source(self, paper_path: Union[Path, str], use_llm = False) -> PaperSource:
		r"""
		Sequentially use `reader_analyze`, `keyword_analyze`, and `llm_analyze` to analyze the paper source

		Args:
			paper_path (Union[Path, str]): The paper path.
			use_llm (bool): Whether to use `llm_analyze`.

		Returns:
			PaperSource
		"""
		source = self.reader_analyze(paper_path)
		if source is None:
			source = self.keyword_analyze(paper_path)
		if source is None and use_llm:
			source = self.llm_analyze(paper_path)
		if source is None:
			source = PaperSource.DEFAULT
		return source
