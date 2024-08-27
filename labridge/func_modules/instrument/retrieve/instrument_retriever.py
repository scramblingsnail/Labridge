from typing import List, Optional, Union, Callable, Tuple

import llama_index.core.instrumentation as instrument

from llama_index.core.schema import MetadataMode
from llama_index.core.llms import LLM
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.schema import (
	NodeWithScore,
	BaseNode,
)

from llama_index.core.settings import Settings
from llama_index.core.indices.utils import default_parse_choice_select_answer_fn

from ..store.instrument_store import InstrumentStorage
from ..prompt.llm_instrument_choice_select import INSTRUMENT_CHOICE_SELECT_PROMPT


dispatcher = instrument.get_dispatcher(__name__)


def format_instrument_node_batch_fn(instrument_nodes: List[BaseNode]) -> str:
	r"""
	This function returns a text containing the indices and descriptions of a batch of instruments.
	LLM will select from these instruments according to this text.

	Args:
		instrument_nodes (List[BaseNode]): The nodes stored in the `InstrumentStorage`,
			containing the instrument name and description.

	Returns:
		str: The generated text.
	"""
	texts = []
	for idx in range(len(instrument_nodes)):
		number = idx + 1
		texts.append(
			f"Instrument {number}:\n"
			f"{instrument_nodes[idx].get_content(metadata_mode=MetadataMode.LLM)}"
		)
	return "\n\n".join(texts)


class InstrumentRetriever:
	r"""
	This is a retriever retrieving in the instrument docs.
	Hybrid retrieving is used.

	Args:
		llm (LLM): The used large language model.
		embed_model (BaseEmbedding): The used embedding model.
		similarity_top_k (int): When retrieving in the vector store, the top-k relevant nodes will be selected.
		instrument_top_k (int): When choosing among the instruments based on their descriptions, the top-k instruments
			will be used.
		final_top_k (int): Finally, retrieving is conducted among the nodes belong to the corresponding instruments
			that are chose in the former content-based retrieving and instrument selection. The top-k nodes will be
			used as the finally retrieved nodes.
	"""
	def __init__(
		self,
		llm: LLM = None,
		embed_model: BaseEmbedding = None,
		similarity_top_k: int = 4,
		instrument_top_k: int = 2,
		final_top_k: int = 3,
		choice_batch_size: int = 8,
	):
		self.llm = llm or Settings.llm
		embed_model = embed_model or Settings.embed_model
		self.instrument_store = InstrumentStorage.from_default(embed_model=embed_model)
		self.vector_index_retriever = self.instrument_store.vector_index.as_retriever(
			similarity_top_k=similarity_top_k,
		)
		self._similarity_top_k = similarity_top_k
		self._instrument_top_k = instrument_top_k
		self._choice_batch_size = choice_batch_size
		self._final_top_k = final_top_k
		self._format_node_batch_fn = format_instrument_node_batch_fn
		self._choice_select_prompt = INSTRUMENT_CHOICE_SELECT_PROMPT
		self._parse_choice_select_answer_fn = default_parse_choice_select_answer_fn

	def _retrieve_proper_instrument(self, retrieve_items: str) -> List[str]:
		r"""
		Use LLM to select the proper instruments based on their description.

		Args:
			retrieve_items (str): The things to be retrieved.

		Returns:
			List[str]:
				The retrieved node_ids.
		"""
		instrument_ids = self.instrument_store.get_all_instruments()
		dsc_nodes = self.instrument_store.get_nodes(node_ids=instrument_ids)

		all_nodes: List[BaseNode] = []
		all_relevances: List[float] = []

		for idx in range(0, len(dsc_nodes), self._choice_batch_size):
			nodes = dsc_nodes[idx: idx + self._choice_batch_size]
			fmt_batch_str = self._format_node_batch_fn(nodes)
			llm_response = self.llm.predict(
				self._choice_select_prompt,
				context_str=fmt_batch_str,
				query_str=retrieve_items,
			)
			choices, relevances = self._parse_choice_select_answer_fn(llm_response, len(nodes))
			choice_indices = [c - 1 for c in choices]

			choice_instruments = [nodes[ci] for ci in choice_indices]

			all_nodes.extend(choice_instruments)
			all_relevances.extend(relevances)

		zipped_list = list(zip(all_nodes, all_relevances))
		sorted_list = sorted(zipped_list, key=lambda x: x[1], reverse=True)
		top_k_list = sorted_list[: self._instrument_top_k]

		select_instrument_ids = [node.node_id for node, relevance in top_k_list]
		return select_instrument_ids

	async def _aretrieve_proper_instrument(self, retrieve_items: str):
		r"""
		Asynchronously select the proper instruments based on their description.

		Args:
			retrieve_items (str): The things to be retrieved.

		Returns:
			List[str]:
				The retrieved node_ids.
		"""
		instrument_ids = self.instrument_store.get_all_instruments()
		dsc_nodes = self.instrument_store.get_nodes(node_ids=instrument_ids)

		all_nodes: List[BaseNode] = []
		all_relevances: List[float] = []

		for idx in range(0, len(dsc_nodes), self._choice_batch_size):
			nodes = dsc_nodes[idx: idx + self._choice_batch_size]
			fmt_batch_str = self._format_node_batch_fn(nodes)
			llm_response = await self.llm.apredict(
				self._choice_select_prompt,
				context_str=fmt_batch_str,
				query_str=retrieve_items,
			)
			choices, relevances = self._parse_choice_select_answer_fn(llm_response, len(nodes))
			choice_indices = [c - 1 for c in choices]

			choice_instruments = [nodes[ci] for ci in choice_indices]

			all_nodes.extend(choice_instruments)
			all_relevances.extend(relevances)

		zipped_list = list(zip(all_nodes, all_relevances))
		sorted_list = sorted(zipped_list, key=lambda x: x[1], reverse=True)
		top_k_list = sorted_list[: self._instrument_top_k]

		select_instrument_ids = [node.node_id for node, relevance in top_k_list]
		return select_instrument_ids

	def set_retriever_top_k(self, similarity_top_k: int):
		r""" Set the top-k of the first content-based retrieving. """
		self.vector_index_retriever._similarity_top_k = similarity_top_k

	def set_retriever_node_ids(self, node_ids: Optional[List[str]] = None):
		r""" Confine the range of node_ids in retrieving. """
		self.vector_index_retriever._node_ids = node_ids

	def _retrieve_instrument_content_based(self, retrieve_items: str) -> List[str]:
		r"""
		Content-based retrieving.

		Args:
			retrieve_items (str): Item to be retrieved.

		Returns:
			List[str]: The ids of the instruments that the retrieved docs belong to.
		"""
		self.set_retriever_top_k(self._similarity_top_k)
		self.set_retriever_node_ids()
		content_nodes = self.vector_index_retriever.retrieve(retrieve_items)

		instrument_ids = set()
		for node in content_nodes:
			instrument_id = node.node.parent_node.node_id
			if instrument_id is not None:
				instrument_ids.add(instrument_id)
		return list(instrument_ids)

	async def _aretrieve_instrument_content_based(self, retrieve_items: str) -> List[str]:
		r"""
		Asynchronously content-based retrieving.

		Args:
			retrieve_items (str): Item to be retrieved.

		Returns:
			List[str]: The ids of the instruments that the retrieved docs belong to.
		"""
		self.set_retriever_top_k(self._similarity_top_k)
		self.set_retriever_node_ids()
		content_nodes = await self.vector_index_retriever.aretrieve(retrieve_items)

		instrument_ids = set()
		for node in content_nodes:
			instrument_id = node.node.parent_node.node_id
			if instrument_id is not None:
				instrument_ids.add(instrument_id)
		return list(instrument_ids)

	@dispatcher.span
	def retrieve(
		self,
		item_to_be_retrieved: str,
	) -> List[NodeWithScore]:
		r"""
		This tool is used to retrieve in the documents of the lab's scientific instruments.
		These documents include the instruction manuals, operation specifications of scientific instruments.

		Args:
			item_to_be_retrieved (str): The string to be retrieved relevant to the scientific instruments

		Returns:
			List[NodeWithScore]: The retrieved nodes.
				The contents of these retrieved nodes will be presented as the output.
		"""
		# This docstring will be used as the tool description.
		dsc_instruments = self._retrieve_proper_instrument(retrieve_items=item_to_be_retrieved)
		content_instruments = self._retrieve_instrument_content_based(retrieve_items=item_to_be_retrieved)

		instrument_ids = list(set(dsc_instruments + content_instruments))
		instruments = self.instrument_store.get_nodes(node_ids=instrument_ids)
		retrieve_range = []

		retrieve_range.extend(instrument_ids)
		for ins in instruments:
			doc_nodes = ins.child_nodes
			if doc_nodes is not None:
				retrieve_range.extend([node.node_id for node in doc_nodes])

		self.set_retriever_top_k(self._final_top_k)
		self.set_retriever_node_ids(node_ids=retrieve_range)
		final_nodes = self.vector_index_retriever.retrieve(item_to_be_retrieved)
		return final_nodes

	async def aretrieve(
		self,
		item_to_be_retrieved: str,
	) -> List[NodeWithScore]:
		r"""
		This tool is used to retrieve in the documents of the lab's scientific instruments.
		These documents include the instruction manuals, operation specifications of scientific instruments.

		Args:
			item_to_be_retrieved (str): The string to be retrieved relevant to the scientific instruments

		Returns:
			List[NodeWithScore]: The retrieved nodes.
				The contents of these retrieved nodes will be presented as the output.
		"""
		# This docstring will be used as the tool description.
		dsc_instruments = await self._aretrieve_proper_instrument(retrieve_items=item_to_be_retrieved)
		content_instruments = await self._aretrieve_instrument_content_based(retrieve_items=item_to_be_retrieved)

		instrument_ids = list(set(dsc_instruments + content_instruments))
		instruments = self.instrument_store.get_nodes(node_ids=instrument_ids)
		retrieve_range = []

		retrieve_range.extend(instrument_ids)
		for ins in instruments:
			doc_nodes = ins.child_nodes
			if doc_nodes is not None:
				retrieve_range.extend([node.node_id for node in doc_nodes])

		self.set_retriever_top_k(self._final_top_k)
		self.set_retriever_node_ids(node_ids=retrieve_range)
		final_nodes = await self.vector_index_retriever.aretrieve(item_to_be_retrieved)
		return final_nodes
