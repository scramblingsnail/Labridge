import json

from llama_index.core.llms import LLM
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.schema import (
	NodeWithScore,
	MetadataMode,
)
from typing import (
	Any,
	List,
	Tuple,
)

from labridge.func_modules.instrument.retrieve.instrument_retriever import InstrumentRetriever
from labridge.func_modules.reference.base import RefInfoBase
from labridge.func_modules.instrument.store.instrument_store import INSTRUMENT_NAME_KEY, INSTRUMENT_ROOT_NODE_NAME
from labridge.accounts.super_users import InstrumentSuperUserManager
from labridge.func_modules.reference.instrument import InstrumentInfo
from labridge.tools.base.tool_base import RetrieverBaseTool, TOOL_LOG_REF_INFO_KEY
from labridge.tools.base.tool_log import ToolLog, TOOL_OP_DESCRIPTION, TOOL_REFERENCES


INSTRUMENT_LOG_KEY = "relevant_instruments"


class InstrumentRetrieverTool(RetrieverBaseTool):
	def __init__(
		self,
		llm: LLM = None,
		embed_model: BaseEmbedding = None,
		metadata_mode: MetadataMode = MetadataMode.NONE,
	):
		instrument_retriever = InstrumentRetriever(
			llm=llm,
			embed_model=embed_model,
		)
		self.metadata_mode = metadata_mode
		self.super_user_manager = InstrumentSuperUserManager()
		super().__init__(
			retriever=instrument_retriever,
			name=InstrumentRetrieverTool.__name__,
			retrieve_fn=InstrumentRetriever.retrieve
		)

	def log(self, log_dict: dict) -> ToolLog:
		ref_infos: List[InstrumentInfo] = log_dict[TOOL_LOG_REF_INFO_KEY]
		instrument_infos = [info.dumps() for info in ref_infos]

		log_to_user = None
		log_to_system = {
			TOOL_OP_DESCRIPTION: f"Use the {self.metadata.name} to retrieve the instrument docs.",
			TOOL_REFERENCES: instrument_infos,
		}

		return ToolLog(
			tool_name=self.metadata.name,
			log_to_user=log_to_user,
			log_to_system=log_to_system,
		)

	def _retrieve(self, retrieve_kwargs: dict) -> List[NodeWithScore]:
		nodes = self._retriever.retrieve(**retrieve_kwargs)
		return nodes

	async def _aretrieve(self, retrieve_kwargs: dict) -> List[NodeWithScore]:
		nodes = await self._retriever.aretrieve(**retrieve_kwargs)
		return nodes

	def get_ref_info(self, nodes: List[NodeWithScore]) -> List[RefInfoBase]:
		r""" Get the reference infos from the retrieved nodes. """
		instrument_infos = []
		instrument_set = set()
		for node in nodes:
			instrument_id = node.metadata.get(INSTRUMENT_NAME_KEY, node.node_id)
			# TODO: Add node type and filter.
			if instrument_id == INSTRUMENT_ROOT_NODE_NAME or instrument_id in instrument_set:
				continue
			instrument_set.add(instrument_id)
			super_users = self.super_user_manager.get_super_users(
				instrument_id=instrument_id,
			)
			info = InstrumentInfo(
				instrument_id=instrument_id,
				super_users=super_users,
			)
			instrument_infos.append(info)
		return instrument_infos

	def _nodes_to_tool_output(self, nodes: List[NodeWithScore]) -> Tuple[str, dict]:
		r""" output the retrieved contents in a specific format. """
		output = ""
		header = f"Have retrieved the docs of several relevant instruments:\n\n"
		output += header

		if len(nodes) < 1:
			output += "No relevant instrument contents found."

		ref_infos = self.get_ref_info(nodes=nodes)
		log_dict = {
			TOOL_LOG_REF_INFO_KEY: ref_infos,
		}

		instrument_docs = dict()
		for node in nodes:
			instrument_id = node.metadata.get(INSTRUMENT_NAME_KEY, node.node_id)
			# TODO: Add node type and filter.
			if instrument_id == INSTRUMENT_ROOT_NODE_NAME:
				continue
			if instrument_id not in instrument_docs:
				instrument_docs[instrument_id] = []
			instrument_docs[instrument_id].append(node)

		for instrument_id in instrument_docs.keys():
			instrument_content = f"Instrument Name: {instrument_id}\n"
			for idx, node in enumerate(instrument_docs[instrument_id]):
				instrument_content += (
					f"Retrieved content {idx + 1}:\n"
					f"{node.node.get_content(metadata_mode=self.metadata_mode)}\n"
			)
			output += f"{instrument_content}\n"
		return output, log_dict


if __name__ == "__main__":
	from labridge.models.utils import get_models

	llm, embed_model = get_models()

	retrieve_tool = InstrumentRetrieverTool(
		llm=llm,
		embed_model=embed_model,
	)
	tool_output = retrieve_tool.call(
		item_to_be_retrieved="如何检查电路板短路",
	)
	print(tool_output.content)
