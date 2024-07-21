from llama_index.core.settings import llm_from_settings_or_context, Settings
from llama_index.core.schema import BaseNode
from llama_index.core.indices.keyword_table import KeywordTableIndex, SimpleKeywordTableIndex, RAKEKeywordTableIndex
from llama_index.core import ServiceContext
from llama_index.core.llms import LLM
from llama_index.core.prompts import PromptTemplate
from llama_index.core.storage import StorageContext

from typing import Sequence, Optional

from .extractors.metadata_extract import PAPER_LEVEL_KEYWORDS
from ...prompt.parse import PAPER_CHUNK_LEVEL_KEYWORD_EXTRACT_TEMPLATE_TMPL



def exclude_all_metadata(nodes: Sequence[BaseNode]):
	for node in nodes:
		node.excluded_llm_metadata_keys = list(node.metadata.keys())


def reset_exclude_metadata(nodes: Sequence[BaseNode]):
	for node in nodes:
		node.excluded_llm_metadata_keys = list()


def copy_paper_keywords(keyword_table_index: KeywordTableIndex, paper_nodes: Sequence[BaseNode]):
	keyword_table = keyword_table_index.index_struct.table
	separator = ', '
	for node in paper_nodes:
		if PAPER_LEVEL_KEYWORDS in node.metadata.keys():
			paper_keywords_list = node.metadata[PAPER_LEVEL_KEYWORDS].split(separator)
			for keyword in paper_keywords_list:
				if keyword not in keyword_table.keys():
					keyword_table[keyword] = set()
				keyword_table[keyword].add(node.node_id)


def get_paper_nodes_keyword_index(paper_nodes: Sequence[BaseNode],
								  max_keywords_num: int,
								  storage_context: Optional[StorageContext],
								  llm: LLM = None,
								  service_context: ServiceContext = None,):
	if llm is None:
		llm = llm_from_settings_or_context(Settings, service_context)

	extract_prompt_tmpl = PromptTemplate(template=PAPER_CHUNK_LEVEL_KEYWORD_EXTRACT_TEMPLATE_TMPL)
	exclude_all_metadata(paper_nodes)
	key_index = KeywordTableIndex(nodes=paper_nodes,
								  llm=llm,
								  storage_context=storage_context,
								  keyword_extract_template=extract_prompt_tmpl,
								  max_keywords_per_chunk=max_keywords_num)
	copy_paper_keywords(keyword_table_index=key_index, paper_nodes=paper_nodes)
	reset_exclude_metadata(paper_nodes)
	return key_index
