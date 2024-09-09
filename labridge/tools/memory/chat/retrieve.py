from llama_index.core.schema import (
	NodeWithScore,
	MetadataMode,
)
from typing import (
	List,
	Tuple,
)

from labridge.func_modules.memory.chat.retrieve import ChatMemoryRetriever
from labridge.func_modules.reference.base import RefInfoBase
from labridge.models.utils import get_models
from labridge.tools.base.tool_base import RetrieverBaseTool
from labridge.tools.base.tool_log import TOOL_OP_DESCRIPTION, TOOL_REFERENCES, ToolLog


CHAT_MEMORY_RETRIEVER_TOOL_NAME = "chat_memory_retriever_tool"


class ChatMemoryRetrieverTool(RetrieverBaseTool):
	r"""
	This tool is used to retrieve in the permanent chat memory of a user or a chat group.

	Args:
		chat_memory_retriever (ChatMemoryRetriever): The chat memory retriever.
		metadata_mode (MetadataMode): The metadata mode, defaults to `MetadataMode.LLM`.
	"""
	def __init__(
		self,
		chat_memory_retriever: ChatMemoryRetriever = None,
		metadata_mode: MetadataMode = MetadataMode.LLM,
	):
		self.metadata_mode = metadata_mode

		chat_memory_retriever = chat_memory_retriever or ChatMemoryRetriever()
		super().__init__(
			retriever=chat_memory_retriever,
			name=ChatMemoryRetrieverTool.__name__,
			retrieve_fn=ChatMemoryRetriever.retrieve,
		)

	def get_ref_info(self, nodes: List[NodeWithScore]) -> List[RefInfoBase]:
		r""" Get the reference infos from the retrieved nodes. """
		return []

	def log(self, log_dict) -> ToolLog:
		r""" tool log """
		item = log_dict["item_to_be_retrieved"]
		memory_id = log_dict["memory_id"]
		start_date = log_dict["start_date"]
		end_date = log_dict["end_date"]
		log_string = (
			f"Using {self.metadata.name} to retrieve '{item}' in the chat history memory with memory_id: '{memory_id}'\n"
			f"Retrieve date is ranging from {start_date} to {end_date}\n"
		)

		log_to_user = None
		log_to_system = {
			TOOL_OP_DESCRIPTION: log_string,
			TOOL_REFERENCES: None,
		}
		return ToolLog(
			tool_name=self.metadata.name,
			log_to_user=log_to_user,
			log_to_system=log_to_system,
		)

	def _retrieve(self, retrieve_kwargs: dict) -> List[NodeWithScore]:
		r""" Use the retriever to retrieve relevant nodes. """
		nodes = self._retriever.retrieve(**retrieve_kwargs)
		return nodes

	async def _aretrieve(self, retrieve_kwargs: dict) -> List[NodeWithScore]:
		r""" Asynchronously use the retriever to retrieve relevant nodes. """
		nodes = await self._retriever.aretrieve(**retrieve_kwargs)
		return nodes

	def _nodes_to_tool_output(self, nodes: List[NodeWithScore]) -> Tuple[str, dict]:
		r""" output the retrieved contents in a specific format. """
		if nodes:
			output = f"Have retrieved relevant conversations in the chat memory\n\n"
			contents = []
			for idx, node in enumerate(nodes):
				node_content = (
					f"Conversation {idx + 1}:\n"
					f"{node.node.get_content(metadata_mode=self.metadata_mode)}"
				)
				contents.append(node_content.strip())
			output += "\n\n".join(contents)
		else:
			output = "No Relevant chat history found."

		output_log = dict()
		return output, output_log


if __name__ == "__main__":
	import asyncio
	from labridge.tools.utils import unpack_tool_output

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

	# results = tool.call(
	# 	item_to_be_retrieved="chat history",
	# 	memory_id="杨再正",
	# 	start_date="2024-07-24",
	# 	end_date="2024-08-08",
	# )
	# tool_output_str, tool_log_str = unpack_tool_output(tool_out_json=results.content)
	# too_log = ToolLog.loads(tool_log_str)
	# print("output:\n", tool_output_str)
	# print("log:\n", too_log.log_to_system)

	async def main():
		results = await tool.acall(
			item_to_be_retrieved="chat history",
			memory_id="杨再正",
			start_date="2024-07-24",
			end_date="2024-08-08",
		)
		tool_output_str, tool_log_str = unpack_tool_output(tool_out_json=results.content)
		too_log = ToolLog.loads(tool_log_str)
		print("output:\n", tool_output_str)
		print("log:\n", too_log.log_to_system)

	asyncio.run(main())


