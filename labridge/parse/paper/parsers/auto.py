from typing import Union
from pathlib import Path


from .default_parser import DefaultPaperParser
from .ieee_parser import IEEEPaperParser
from .nature_parser import NaturePaperParser
from ..extractors.source_analyze import PaperSource

from ..extractors.source_analyze import PaperSourceAnalyzer


def auto_parse_paper(file_path: Union[str, Path],
					 source_analyzer: PaperSourceAnalyzer,
					 use_llm_for_source: bool):
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
