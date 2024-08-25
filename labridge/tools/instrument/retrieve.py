import json

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
from labridge.func_modules.instrument.store.instrument_store import INSTRUMENT_NAME_KEY
from labridge.accounts.super_users import InstrumentSuperUserManager
from labridge.models.utils import get_models
from labridge.func_modules.reference.instrument import InstrumentInfo
from labridge.tools.base.tool_base import RetrieverBaseTool
from labridge.tools.base.tool_log import ToolLog, TOOL_OP_DESCRIPTION, TOOL_REFERENCES


INSTRUMENT_RETRIEVER_TOOL_NAME = "chat_memory_retriever_tool"
INSTRUMENT_LOG_KEY = "relevant_instruments"


class InstrumentRetrieverTool(RetrieverBaseTool):
	def __init__(
		self,
		instrument_retriever: InstrumentRetriever = None,
		metadata_mode: MetadataMode = MetadataMode.NONE,
	):
		instrument_retriever = instrument_retriever or InstrumentRetriever()
		self.metadata_mode = metadata_mode
		self.super_user_manager = InstrumentSuperUserManager()
		super().__init__(
			retriever=instrument_retriever,
			name=INSTRUMENT_RETRIEVER_TOOL_NAME,
			retrieve_fn=InstrumentRetriever.retrieve
		)

	def log(self, log_dict: dict) -> ToolLog:
		instruments = log_dict[INSTRUMENT_LOG_KEY]
		instrument_infos = []
		for instrument_id in instruments.keys():
			super_users = instruments[instrument_id]
			info = InstrumentInfo(
				instrument_id=instrument_id,
				super_users=super_users,
			)
			instrument_infos.append(info.dumps())

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

	def _aretrieve(self, retrieve_kwargs: dict) -> List[NodeWithScore]:
		nodes = await self._retriever.aretrieve(**retrieve_kwargs)
		return nodes

	def _nodes_to_tool_output(self, nodes: List[NodeWithScore]) -> Tuple[str, dict]:
		r""" output the retrieved contents in a specific format. """
		output = ""
		header = f"Have retrieved the docs of several relevant instruments:\n\n"
		output += header

		if len(nodes) < 1:
			output += "No relevant instrument contents found."

		instrument_docs = dict()
		output_log_dict = {INSTRUMENT_LOG_KEY: dict()}
		for node in nodes:
			instrument_id = node.metadata[INSTRUMENT_NAME_KEY]
			if instrument_id not in instrument_docs:
				instrument_docs[instrument_id] = []
				output_log_dict[INSTRUMENT_LOG_KEY][instrument_id] = self.super_user_manager.get_super_users(
					instrument_id=instrument_id,
				)
			instrument_docs[instrument_id].append(node)

		for instrument_id in instrument_docs.keys():
			instrument_content = f"Instrument Name: {instrument_id}\n"
			for idx, node in enumerate(instrument_docs[instrument_id]):
				instrument_content += (
					f"Retrieved content {idx + 1}:\n"
					f"{node.node.get_content(metadata_mode=self.metadata_mode)}\n"
			)
			output += f"{instrument_content}\n"
		return output, output_log_dict


if __name__ == "__main__":
	# TODO:
	a = 1