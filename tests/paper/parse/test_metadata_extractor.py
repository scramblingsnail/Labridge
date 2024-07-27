from pathlib import Path

from labridge.paper.parse.extractors.metadata_extract import PaperMetadataExtractor
from labridge.llm.models import get_models


def test_extract_paper_metadata():
	llm, embed_model = get_models()
	rr = PaperMetadataExtractor(llm=llm)

	root = Path(__file__)
	for i in range(4):
		root = root.parent

	pdf_path = root / "docs/papers/杨再正/存算一体/Fully hardware-implemented memristor CNN.pdf"
	paper_metadata = rr.extract_paper_metadata(pdf_path=pdf_path)
	print(paper_metadata)


if __name__ == "__main__":
	test_extract_paper_metadata()
