from llama_index.core.schema import Document
from typing import Union, List
from pathlib import Path

from .default_parser import DefaultPaperParser
from .ieee_parser import IEEEPaperParser
from .nature_parser import NaturePaperParser
from ..extractors.source_analyze import PaperSource

from ..extractors.source_analyze import PaperSourceAnalyzer


def auto_parse_paper(
	file_path: Union[str, Path],
	source_analyzer: PaperSourceAnalyzer,
	use_llm_for_source: bool,
) -> List[Document]:
	r"""
	Automatically parse a paper according to the analyzed paper source.

	Args:
		file_path (Union[str, Path]): The paper path.
		source_analyzer (PaperSourceAnalyzer): The analyzer that analyze the paper source.
		use_llm_for_source (bool): Whether to use LLM in the source_analyzer.

	Returns:
		List[Document]: The parsed paper documents.
			For example: A paper from Nature will be seperated into these components:
			`ABSTRACT`, `MAINTEXT`, `REFERENCES`, `METHODS`.
	"""
	paper_source = source_analyzer.analyze_source(file_path, use_llm_for_source)

	if paper_source == PaperSource.NATURE:
		parser = NaturePaperParser()
	elif paper_source == PaperSource.IEEE:
		parser = IEEEPaperParser()
	elif paper_source == PaperSource.DEFAULT:
		parser = DefaultPaperParser()
	else:
		raise ValueError("Invalid paper source.")

	docs = parser.parse_paper(file_path=file_path)
	return docs
