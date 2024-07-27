from pathlib import Path

from labridge.paper.parse.parsers.ieee_parser import IEEEPaperParser, IEEE_CONTENT_NAMES
from labridge.paper.parse.parsers.base import CONTENT_TYPE_NAME


article_list = [
	"docs/papers/张三/深度学习编译/"
	"The_Deep_Learning_Compiler_A_Comprehensive_Survey.pdf",
	"docs/papers/张三/深度学习编译/"
	"Towards Efficient Generative Large Language Model Serving-A Survey from Algorithms to Systems.pdf",
	"docs/papers/张三/深度学习编译/CIM/"
	"A Compilation Tool for Computation Offloading in ReRAM-based CIM Architectures.pdf",
	"docs/papers/张三/深度学习编译/CIM/"
	"A_Compilation_Framework_for_SRAM_Computing-in-Memory_Systems_With_Optimized_Weight_Mapping_and_Error_Correction.pdf",
	"docs/papers/张三/深度学习编译/CIM/"
	"C4CAM_ACompiler for CAM-based In-memory Accelerators.pdf",
	"docs/papers/张三/深度学习编译/CIM/"
	"CIM-MLC_AMulti-level Compilation Stack for Computing-in-memory accelerators.pdf",
]

review_list = [
	"docs/papers/张三/深度学习编译/An_In-depth_Comparison_of_Compilers_for_Deep_Neural_Networks_on_Hardware.pdf",
]



if __name__ == "__main__":
	parser = IEEEPaperParser(separator_tolerance=5)

	root = Path(__file__)
	for i in range(4):
		root = root.parent

	for paper in article_list + review_list:
		paper_path = root / paper
		documents = parser.parse_paper(paper_path)
		title = parser.parse_title(paper_path)
		print("\n\n>>> Title: \n", title)
		num = len(documents)
		for idx, doc in enumerate(documents):
			print(f"\n>>> {doc.metadata[CONTENT_TYPE_NAME]}: \n", doc.text[:1000])