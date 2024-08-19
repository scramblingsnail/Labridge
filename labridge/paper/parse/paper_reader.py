# This file is used to read research papers with pdf format to Document.
# Author: zhi-san
# E-mail: 762598802@qq.com

import logging
import fsspec

from fsspec.implementations.local import LocalFileSystem
from typing import Dict, List, Optional, Union, Tuple
from pathlib import Path, PurePosixPath

from llama_index.core.settings import llm_from_settings_or_context
from llama_index.core.schema import TransformComponent, Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core import ServiceContext, Settings
from llama_index.core.readers.file.base import is_default_fs
from llama_index.core.utils import print_text
from llama_index.core.llms import LLM

from .parsers.base import MetadataContents, ChunkContents, CONTENT_TYPE_NAME
from .parsers.auto import auto_parse_paper
from .extractors.source_analyze import PaperSourceAnalyzer
from .extractors.metadata_extract import (
	PaperMetadataExtractor,
	PAPER_POSSESSOR,
	PAPER_REL_FILE_PATH,
)


logger = logging.getLogger(__name__)



class PaperReader:
	r"""
	Read a PDF paper, and extract valid meta_data from it.

	Args:
		llm (LLM: the used llm, if not provided, use the llm from `service_context`.
			Defaults to None.
		source_keyword_threshold (int): used in PaperSourceAnalyzer. refer to PaperSourceAnalyzer for details.
			Defaults to 10
		use_llm_for_source (bool): whether to use LLM in the source analyzer. Defaults to True.
		extract_metadata (bool): whether to use LLM to extract metadata for papers. Defaults to True.
		necessary_metadata (Dict[str, str]): Paper level metadata.
			The necessary metadata that must be extracted.
		 	It is a dictionary with k-v pairs like: {metadata_name: description}. The description
		 	is used to instruct the llm to extract the corresponding metadata.
		 	For example:

		 	- key: "Title"
		 	- value: "The title often appears as a single concise sentence at the head of a paper."
		optional_metadata (Dict[str, str]): Paper level metadata.
			The optional metadata that is not forced to extract from the paper.
			It is a dictionary with k-v pairs like: {metadata_name: description}.
		extract_retry_times: max retry times if not all necessary metadata is extracted.
		service_context (ServiceContext): the service context.
		recursive (bool): Whether to recursively search in subdirectories.
            False by default.
		exclude (List): glob of python file paths to exclude (Optional)
        exclude_hidden (bool): Whether to exclude hidden files (dotfiles).
        required_exts (Optional[List[str]]): List of required extensions.
            Default is None.
        num_files_limit (Optional[int]): Maximum number of files to read.
            Default is None.
		filename_as_id (bool): whether to use the filename as the document id. True by default.
			If set to True, the doc node will be named as `{file_path}_{content_type}`.
			The file_path is relative to root directory.
	"""
	def __init__(self,
				 llm: LLM = None,
				 source_keyword_threshold: int = 10,
				 use_llm_for_source: bool = True,
				 extract_metadata: bool = True,
				 necessary_metadata: Dict[str, str] = None,
				 optional_metadata: Dict[str, str] = None,
				 extract_retry_times: int = 2,
				 filename_as_id: bool = True,
				 service_context: ServiceContext = None,
				 recursive: bool = False,
				 exclude: Optional[List] = None,
				 exclude_hidden: bool = True,
				 required_exts: Optional[List[str]] = None,
				 num_files_limit: Optional[int] = None,
				 fs: Optional[fsspec.AbstractFileSystem] = None,):

		self.metadata_extractor = None
		self.extract_metadata = extract_metadata
		if extract_metadata:
			self.metadata_extractor = PaperMetadataExtractor(llm=llm,
															 necessary_metadata=necessary_metadata,
															 optional_metadata=optional_metadata,
															 max_retry_times=extract_retry_times,
															 service_context=service_context)
		if llm is None:
			self.llm = llm_from_settings_or_context(Settings, service_context)
		else:
			self.llm = llm

		self.source_analyzer = PaperSourceAnalyzer(llm=self.llm, keyword_count_threshold=source_keyword_threshold)
		self.use_llm_for_source = use_llm_for_source
		self.filename_as_id = filename_as_id
		self.recursive = recursive
		self.exclude = exclude
		self.exclude_hidden = exclude_hidden
		self.required_exts = required_exts
		self.num_files_limit = num_files_limit
		self.fs = fs or LocalFileSystem()
		root = Path(__file__)
		for i in range(4):
			root = root.parent
		self.root = root

	def get_paper_possessor(self, paper_path: Union[Path, str]) -> str:
		r"""
		Get the possessor of this paper.

		Assume the possessor is the first level directory under the paper warehouse.
		"""
		if isinstance(paper_path, str):
			paper_path = Path(paper_path)
		paper_warehouse = self.root / "docs/papers"
		rel = paper_path.relative_to(paper_warehouse)
		possessor = str(rel).split('/')[0]
		return possessor

	def read_single_paper(self,
						  file_path: Union[Path, str],
						  show_progress: bool = True) -> Tuple[List[Document], List[Document]]:
		r"""
		Read a single pdf paper.
		
		Args:
		 	file_path (Union[Path, str]): the path of pdf paper.
		 	show_progress (bool): show parsing progress.

		Returns:
			Tuple[List[Document], List[Document]]:
				The ingested content docs and extra docs.

				- chunk_docs: the docs for retrieving, include information such as main text, methods.
				Might be None if nothing is parsed (auto_parse_paper fails.)
				- extra_docs: docs that involve supplementary information such as references.
				Might be None.
		"""
		if isinstance(file_path, str):
			file_path = Path(file_path)
		if str(file_path)[-4:] != '.pdf':
			raise ValueError("Expect a PDF file.")
		if show_progress:
			print_text(f">>> Loading {file_path}", color="blue", end="\n")
		parsed_docs = auto_parse_paper(
			file_path=file_path,
			source_analyzer=self.source_analyzer,
			use_llm_for_source=self.use_llm_for_source
		)

		chunk_docs, extra_docs, metadata_docs = [], [], []
		for doc in parsed_docs:
			if doc.metadata[CONTENT_TYPE_NAME] in MetadataContents:
				metadata_docs.append(doc)
			elif doc.metadata[CONTENT_TYPE_NAME] in ChunkContents:
				chunk_docs.append(doc)
			else:
				extra_docs.append(doc)

		# metadata
		paper_metadata = dict()

		if self.extract_metadata:
			paper_metadata = self.metadata_extractor.extract_paper_metadata(pdf_path=file_path)
			for meta_doc in metadata_docs:
				metadata_name = meta_doc.metadata[CONTENT_TYPE_NAME]
				if metadata_name not in paper_metadata.keys():
					paper_metadata[metadata_name] = meta_doc.text

		possessor = self.get_paper_possessor(file_path)
		paper_metadata[PAPER_POSSESSOR] = possessor
		paper_metadata[PAPER_REL_FILE_PATH] = str(file_path.relative_to(self.root))

		for idx, doc in enumerate(parsed_docs):
			doc.metadata.update(paper_metadata)
			if self.filename_as_id:
				rel_path = str(file_path.relative_to(self.root))
				doc.id_ = f"{rel_path!s}_{doc.metadata[CONTENT_TYPE_NAME]}"
		return chunk_docs, extra_docs

	def read_papers(self,
					input_dir: Optional[str] = None,
					input_files: Optional[List] = None,
					show_progress: bool = True) -> Tuple[List[Document], List[Document]]:
		r"""
		Read papers.

		Args:
			input_dir (Optional[str]): the paper directory.
			input_files (Optional[List]): the paths of papers. If it is specified, the `input_dir` is ignored.
			show_progress (bool): show parsing progress.

		Returns:
			Tuple[List[Document], List[Document]]:
				the content docs and the extra docs.

				- contents: for retrieving, each sequence in the list contains the content docs of a paper.
				- extra_info: extra info, each sequence in the list contains the extra docs of a paper.
		"""
		_Path = Path if is_default_fs(self.fs) else PurePosixPath
		paper_files = None
		if input_files:
			paper_files = []
			for path in input_files:
				if not self.fs.isfile(path):
					raise ValueError(f"File {path} does not exist.")
				input_file = _Path(path)
				paper_files.append(input_file)
		elif input_dir:
			if not self.fs.isdir(input_dir):
				raise ValueError(f"Directory {input_dir} does not exist.")
			input_dir = _Path(input_dir)
			paper_files = self._add_files(input_dir)

		contents, extra_info = [], []
		if paper_files is not None:
			for idx, paper in enumerate(paper_files):
				if str(paper)[-4:] != '.pdf':
					continue
				content_docs, extra_docs = self.read_single_paper(file_path=paper, show_progress=show_progress)
				contents += content_docs
				extra_info += extra_docs
		return contents, extra_info

	def is_hidden(self, path: Path) -> bool:
		return any(part.startswith(".") and part not in [".", ".."] for part in path.parts)

	def _add_files(self, input_dir: Path) -> List[Path]:
		"""Add files."""
		all_files = set()
		rejected_files = set()
		rejected_dirs = set()
		# Default to POSIX paths for non-default file systems (e.g. S3)
		_Path = Path if is_default_fs(self.fs) else PurePosixPath

		if self.exclude is not None:
			for excluded_pattern in self.exclude:
				if self.recursive:
					# Recursive glob
					excluded_glob = _Path(input_dir) / _Path("**") / excluded_pattern
				else:
					# Non-recursive glob
					excluded_glob = _Path(input_dir) / excluded_pattern
				for file in self.fs.glob(str(excluded_glob)):
					if self.fs.isdir(file):
						rejected_dirs.add(_Path(file))
					else:
						rejected_files.add(_Path(file))

		file_refs: List[str] = []
		if self.recursive:
			file_refs = self.fs.glob(str(input_dir) + "/**/*")
		else:
			file_refs = self.fs.glob(str(input_dir) + "/*")

		for ref in file_refs:
			# Manually check if file is hidden or directory instead of
			# in glob for backwards compatibility.
			ref = _Path(ref)
			is_dir = self.fs.isdir(ref)
			skip_because_hidden = self.exclude_hidden and self.is_hidden(ref)
			skip_because_bad_ext = (self.required_exts is not None and ref.suffix not in self.required_exts)
			skip_because_excluded = ref in rejected_files
			if not skip_because_excluded:
				if is_dir:
					ref_parent_dir = ref
				else:
					ref_parent_dir = self.fs._parent(ref)
				for rejected_dir in rejected_dirs:
					if str(ref_parent_dir).startswith(str(rejected_dir)):
						skip_because_excluded = True
						logger.debug("Skipping %s because it in parent dir %s which is in %s", ref, ref_parent_dir,
							rejected_dir, )
						break

			if (is_dir or skip_because_hidden or skip_because_bad_ext or skip_because_excluded):
				continue
			else:
				all_files.add(ref)

		new_input_files = sorted(all_files)

		if len(new_input_files) == 0:
			raise ValueError(f"No files found in {input_dir}.")

		if self.num_files_limit is not None and self.num_files_limit > 0:
			new_input_files = new_input_files[0: self.num_files_limit]

		# print total number of files added
		logger.debug(f"> [PaperReader] Total files added: {len(new_input_files)}")

		return new_input_files
