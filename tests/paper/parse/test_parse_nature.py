from pathlib import Path

from labridge.paper.parse.parsers.nature_parser import NaturePaperParser, NATURE_CONTENT_NAMES
from labridge.paper.parse.parsers.base import CONTENT_TYPE_NAME


article_list = [
	"docs/papers/杨再正/存算一体/Fully hardware-implemented memristor CNN.pdf",
	"docs/papers/张三/强化学习/alpha star.pdf",
	"docs/papers/张三/强化学习/Human-level control through deep reinforcement learning.pdf",
	"docs/papers/杨再正/存算一体/"
	"2020 lin peng Three-dimensional memristor circuits as complex networks.pdf",
	"docs/papers/杨再正/存算一体/"
	"2018 NC Efficient and self-adaptive in-situ learning in multilayer memristor neural networks.pdf",
	"docs/papers/杨再正/存算一体/"
	"2019 wangzhongrui In situ training of feed-forward and recurrent convolutional memristor network.pdf",
	"docs/papers/杨再正/存算一体/Reinforcement learning with analogue memristor arrays.pdf",
]

review_list = [
	"docs/papers/杨再正/存算一体/Memristive crossbar arrays for brain-inspired computing.pdf",
]


if __name__ == "__main__":
	parser = NaturePaperParser()

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
			print(f"\n>>> {doc.metadata[CONTENT_TYPE_NAME]}: \n", doc.text[:8000])