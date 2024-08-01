import json

from llama_index.core.schema import (
	NodeWithScore,
	MetadataMode,
)
from typing import (
	Any,
	List,
)

from labridge.memory.chat.retrieve import ChatMemoryRetriever
from labridge.llm.models import get_models
from ..base import RetrieverBaseTool


CHAT_MEMORY_RETRIEVER_TOOL_NAME = "chat_memory_retriever_tool"


class ChatMemoryRetrieverTool(RetrieverBaseTool):
	def __init__(
		self,
		chat_memory_retriever: ChatMemoryRetriever = None,
		metadata_mode: MetadataMode = MetadataMode.LLM,

	):
		self.metadata_mode = metadata_mode

		chat_memory_retriever = chat_memory_retriever or ChatMemoryRetriever()
		super().__init__(
			retriever=chat_memory_retriever,
			name=CHAT_MEMORY_RETRIEVER_TOOL_NAME,
			retrieve_fn=ChatMemoryRetriever.retrieve_with_date,
		)

	def log(self, retrieve_kwargs) -> str:
		r""" tool log """
		item = retrieve_kwargs["item_to_be_retrieved"]
		memory_id = retrieve_kwargs["memory_id"]
		start_date = retrieve_kwargs["start_date"]
		end_date = retrieve_kwargs["end_date"]
		tool_log = (
			f"Using {self.metadata.name} to retrieve '{item}' in the chat history memory with memory_id: '{memory_id}'\n"
			f"Retrieve date is ranging from {start_date} to {end_date}\n"
		)
		return json.dumps(tool_log)

	def _get_retriever_input(self, *args: Any, **kwargs: Any) -> dict:
		r""" Parse the input of the call method to the input of the retrieve method of the retriever. """
		required_kwargs = [
			"item_to_be_retrieved",
			"memory_id",
			"start_date",
			"end_date",
		]

		missing_keys = []
		for key in required_kwargs:
			if key not in kwargs:
				missing_keys.append(key)
		if len(missing_keys) > 0:
			raise ValueError(f"The required parameters are not provided: {','.join(missing_keys)}")

		retrieve_kwargs = {
			"item_to_be_retrieved": kwargs["item_to_be_retrieved"],
			"memory_id": kwargs["memory_id"],
			"start_date": kwargs["start_date"],
			"end_date": kwargs["end_date"],
		}
		return retrieve_kwargs

	def _retrieve(self, retrieve_kwargs: dict) -> List[NodeWithScore]:
		r""" Use the retriever to retrieve relevant nodes. """
		nodes = self._retriever.retrieve_with_date(**retrieve_kwargs)
		return nodes

	async def _aretrieve(self, retrieve_kwargs: dict) -> List[NodeWithScore]:
		r""" Asynchronously use the retriever to retrieve relevant nodes. """
		nodes = await self._retriever.aretrieve_with_date(**retrieve_kwargs)
		return nodes

	def _nodes_to_tool_output(self, nodes: List[NodeWithScore]) -> str:
		r""" output the retrieved contents in a specific format. """
		output = ""
		header = f"Have retrieved relevant conversations in the chat memory\n\n"
		output += header

		if len(nodes) < 1:
			output += "No Chat history found."

		for idx, node in enumerate(nodes):
			node_content = (
				f"Conversation {idx + 1}:\n"
				f"{node.node.get_content(metadata_mode=self.metadata_mode)}\n\n"
			)
			output += node_content
		return output


if __name__ == "__main__":
	llm, embed_model = get_models()

	chat_retriever = ChatMemoryRetriever(
		embed_model=embed_model,
		# relevant_top_k=2,
		final_use_context=False,
	)
	tool = ChatMemoryRetrieverTool(chat_memory_retriever=chat_retriever)
	print(tool.metadata.name)
	print(tool.metadata.description)
	print(tool.metadata.fn_schema_str)

	results =tool.call(
		item_to_be_retrieved="chat history",
		memory_id="杨再正",
		start_date="2024-07-24",
		end_date="2024-07-24",
	)

	print(results.content)

