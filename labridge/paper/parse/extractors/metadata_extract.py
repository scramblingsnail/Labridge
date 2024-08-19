from llama_index.core.settings import llm_from_settings_or_context
from llama_index.core.schema import Document, TransformComponent
from llama_index.readers.file.pymu_pdf import PyMuPDFReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.extractors import KeywordExtractor
from llama_index.core import ServiceContext, Settings
from llama_index.core.utils import print_text
from llama_index.core.llms import LLM

from typing import Dict, List, Union, Tuple
from pathlib import Path

from ....common.query_engine.query_engines import SingleQueryEngine


r""" a dictionary of {'metadata': 'description'} """
PAPER_REL_FILE_PATH = "File path"
PAPER_LEVEL_KEYWORDS = "Paper keywords"
PAPER_TITLE = "Title"
PAPER_POSSESSOR = "Possessor"

DEFAULT_NECESSARY_METADATA = {
	PAPER_TITLE: "The title often appears as a single concise sentence at the head of a paper.",
	"Abstract": "abstract often appears as the first paragraph in the text of a paper. "
				"It generally includes 100 to 300 words. Use the original text",
	"Authors": "The authors name often appears at the header of a paper, following the title."
			   "And the name of authors are separated by separators such as commas.",
	PAPER_LEVEL_KEYWORDS: "You must extract several keywords of the paper. "
						  "Output the keywords in a comma-separated format.",
}

DEFAULT_OPTIONAL_METADATA = {
	"Paper type": "You'd better judge whether the paper is a review(survey) or an article. \n"
				  "A review(survey) summarizes, synthesizes, and evaluates existing research on a particular topic."
				  "Besides, in a review, the keywords 'review' or 'survey' generally appear in its Abstract or Title, "
				  "it's a simple way to judge whether it is a review or not.\n"
				  "An article inform, educate, or present original research findings.\n",
	"Institutes": "The institute of the authors, often appears with the authors at the head of the paper.",
	"Publish year": "The publication year of the paper."
}


class PaperMetadataExtractor:
	def __init__(self,
				 llm: LLM = None,
				 necessary_metadata: Dict[str, str] = None,
				 optional_metadata: Dict[str, str] = None,
				 max_retry_times: int = 2,
				 service_context: ServiceContext = None,):
		self.necessary_metadata = necessary_metadata or DEFAULT_NECESSARY_METADATA
		self.optional_metadata = optional_metadata or DEFAULT_OPTIONAL_METADATA
		if llm is None:
			self.llm = llm_from_settings_or_context(Settings, service_context)
		else:
			self.llm = llm

		self.prompt_tmpl = self.get_prompt_tmpl()
		self.query_engine = SingleQueryEngine(llm=llm, prompt_tmpl=self.prompt_tmpl)
		self.max_retry_times = max_retry_times

	def _default_transformations(self) -> List[TransformComponent]:
		return [
				SentenceSplitter(chunk_size=1024, chunk_overlap=256, include_metadata=True),
				KeywordExtractor(keywords=5, llm=self.llm),
			]

	def get_prompt_tmpl(self,
						necessary_metadata: Dict[str, str] = None,
						optional_metadata: Dict[str, str] = None) -> str:
		r"""
		This function is used to get the prompt template used for extracting metadata, according to the
		`necessary_metadata` and `optional_metadata`.
		"""

		necessary_metadata = necessary_metadata or self.necessary_metadata
		optional_metadata = optional_metadata or self.optional_metadata

		tmpl = ("Here is the first page of a research paper. "
				"You need try to extract some information from it.\n\n"
				"The NECESSARY metadata that you MUST extract contain:\n")
		necessary_metadata_names = ', '.join(list(necessary_metadata.keys()))
		tmpl += necessary_metadata_names
		tmpl += ("\n\nIt is better to extract the following metadata,"
				 "But if a optional metadata does not appear in the paper, you do not need to output it.\n")
		optional_metadata_names = ', '.join(list(optional_metadata.keys()))
		tmpl += optional_metadata_names
		tmpl += ("\n\n"
				 "Here are some suggestions for you to extract these metadata:")
		tmpl += "\n\nSuggestions for extracting NECESSARY metadata:\n"

		for key in necessary_metadata.keys():
			tmpl += f"**{key}**: {necessary_metadata[key]}\n"

		tmpl += ("\n\n"
				 "Suggestions for extracting optional metadata:\n")
		for key in optional_metadata.keys():
			tmpl += f"**{key}**: {optional_metadata[key]}\n"
		tmpl += ("\n\n"
				 "The first page of the paper is as follows:\n"
				 "{}")
		tmpl += ("\n\nOutput your extracted metadata as the following FORMAT:\n"
				 "**metadata_name**: <extracted corresponding metadata>\n\n"
				 "List your extracted metadata as follows:\n\n")

		for key in necessary_metadata.keys():
			tmpl += f"**{key}**: \n\n"
		for key in optional_metadata.keys():
			tmpl += f"**{key}**: \n\n"
		return tmpl

	def _set_query_prompt(self,
						  necessary_metadata: Dict[str, str] = None,
						  optional_metadata: Dict[str, str] = None,):
		r""" If both `necessary_metadata` and `optional_metadata` are None, set the default prompt. """
		self.query_engine.prompt_tmpl = self.get_prompt_tmpl(necessary_metadata, optional_metadata)

	def metadata_output_format(self, llm_answer: str) -> Dict[str, str]:
		r"""
		The LLM is supposed to answer like this:

		- **metadata_name 1**: extracted metadata 1.
		- **metadata_name 2**: extracted metadata 2.

		Extract a metadata dictionary from the answer of llm.
		"""

		str_list = llm_answer.split("**")
		metadata = dict()

		idx = 0
		# key: 1 v: 2
		while 2 * idx + 2 < len(str_list):
			key = str_list[2 * idx + 1]
			val = str_list[2 * idx + 2]
			key = key.replace("\n", "")
			val = val.replace("\n", "")
			if key in self.necessary_metadata.keys() or key in self.optional_metadata.keys():
				metadata[key] = val.replace(": ", "", 1)
			idx += 1
		return metadata

	def _extract_metadata(self,
						 pdf_path: Union[Path, str] = None,
						 pdf_docs: List[Document] = None,
						 necessary_metadata: Dict[str, str] = None,
						 optional_metadata: Dict[str, str] = None,
						 ) -> Dict[str, str]:
		r"""
		Use the LLM to extract metadata of a paper.

		Args:
			pdf_path: (Union[Path, str]): the path of a pdf paper.
			pdf_docs (List[Document]): the documents of a pdf paper.
			necessary_metadata (Dict[str, str]):
			optional_metadata (optional_metadata):

		Returns:
			metadata (Dict[str, str]): The extracted meta data.

		"""

		if pdf_path is not None:
			pdf_docs = PyMuPDFReader().load_data(file_path=pdf_path)
		elif pdf_docs is None:
			raise ValueError("pdf_path and pdf_docs can not both be None.")

		first_page = pdf_docs[0].text
		self._set_query_prompt(necessary_metadata, optional_metadata)
		response = self.query_engine.query(first_page)
		# reset prompt
		self._set_query_prompt()
		extract_text = response.response
		metadata = self.metadata_output_format(extract_text)
		return metadata

	def _lacked_metadata(self, paper_metadata: Dict[str, str]) -> Tuple[Dict, Dict]:
		lack_necessary_keys = set(self.necessary_metadata.keys()) - set(paper_metadata.keys())
		lack_optional_keys = set(self.optional_metadata.keys()) - set(paper_metadata.keys())

		lack_necessary_metadata = dict()
		lack_optional_metadata = dict()
		for key in lack_necessary_keys:
			lack_necessary_metadata.update({key: self.necessary_metadata[key]})

		for key in lack_optional_keys:
			lack_optional_metadata.update({key: self.optional_metadata[key]})

		return lack_necessary_metadata, lack_optional_metadata

	def extract_paper_metadata(self,
							   pdf_path: Union[Path, str] = None,
							   pdf_docs: List[Document] = None,
							   show_progress: bool = True,):
		if pdf_path:
			pdf_docs = PyMuPDFReader().load_data(file_path=pdf_path)
		elif pdf_docs is None:
			raise ValueError("pdf_path and pdf_docs can not both be None.")

		paper_metadata = dict()
		lack_necessary_metadata, _ = self.necessary_metadata, self.optional_metadata
		retry_count = 0
		while len(lack_necessary_metadata.keys()) > 0 and retry_count <= self.max_retry_times:
			new_metadata = self._extract_metadata(pdf_docs=pdf_docs,
												  necessary_metadata=lack_necessary_metadata,
												  optional_metadata=self.optional_metadata)
			retry_count += 1
			if show_progress:
				print_text(f">>>\tExtract try idx {retry_count}: {list(new_metadata.keys())}", color="cyan", end="\n")
			paper_metadata.update(new_metadata)
			lack_necessary_metadata, _ = self._lacked_metadata(paper_metadata)
		return paper_metadata




