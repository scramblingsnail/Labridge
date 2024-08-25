import fsspec

from pathlib import Path
from typing import List, Optional

from llama_index.core.indices.vector_store import VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core import load_index_from_storage
from llama_index.core.storage import StorageContext
from llama_index.core.bridge.pydantic import Field
from llama_index.core import Settings
from llama_index.core.schema import (
	TextNode,
	NodeRelationship,
	RelatedNodeInfo,
	BaseNode,
	MetadataMode,
)
from llama_index.core.memory.vector_memory import (
	VectorMemory,
	_get_starter_node_for_new_batch,
	_stringify_chat_message,
)
from llama_index.core.base.llms.types import (
	ChatMessage,
	MessageRole,
)

from labridge.accounts.users import AccountManager
from labridge.common.utils.time import get_time
from labridge.models.utils import get_models
from labridge.func_modules.memory.base import LOG_DATE_NAME, LOG_TIME_NAME


CHAT_MEMORY_PERSIST_DIR = "storage/chat_memory"
CHAT_MEMORY_VECTOR_INDEX_ID = "chat_memory"

MEMORY_FIRST_NODE_NAME = "init_node"
CHAT_GROUP_MEMBERS_NODE_NAME = "members"
MEMORY_LAST_NODE_ID_NAME = "last_node_id"


class ChatVectorMemory(VectorMemory):
	r"""
	This class is used to store the chat history, involving the logs of called tools in chat.

	Args:
		vector_index (VectorStoreIndex): The vector database.
		retriever_kwargs (dict): Not used. Refer to `ChatMemoryRetriever`.
		persist_dir (str): The save directory.

	Note:
		In the vector index, the metadata `LOG_DATE_NAME` and `LOG_TIME_NAME` are recorded for each chat log node, they are
		useful for filtering in retrieving.
		The metadata `date` and `time` is recorded in a list format for the convenience of metadata filtering.
		For example: ['2024-08-10'], ['09:05:03'].
	"""
	persist_dir: str = Field(
		default="",
		description="The persist dir of the memory index relative to the root.",
	)
	def __init__(
		self,
		vector_index: VectorStoreIndex,
		retriever_kwargs: dict,
		persist_dir: str
	):
		super().__init__(vector_index=vector_index, retriever_kwargs=retriever_kwargs)
		self.vector_index.set_index_id(CHAT_MEMORY_VECTOR_INDEX_ID)
		self.persist_dir = persist_dir

	@classmethod
	def from_storage(
		cls,
		persist_dir: str,
		embed_model: BaseEmbedding,
		retriever_kwargs: dict,
	):
		r"""
		Load from an existing storage.

		Args:
			persist_dir (str): The save path of the storage.
			embed_model (BaseEmbedding): The used embedding model.
			retriever_kwargs (dict): Not used.

		Returns:
			ChatVectorMemory
		"""
		vector_storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
		vector_index = load_index_from_storage(
			storage_context=vector_storage_context,
			index_id=CHAT_MEMORY_VECTOR_INDEX_ID,
			embed_model=embed_model,
		)
		return cls(
			vector_index=vector_index,
			retriever_kwargs=retriever_kwargs,
			persist_dir=persist_dir,
		)

	@property
	def memory_id(self) -> str:
		r"""
		The memory_id is either a user_id or a chat_group_id.

		Returns:
			str: The memory id of this ChatMemory.
		"""
		root = Path(__file__)
		for idx in range(5):
			root = root.parent

		mem_id = Path(self.persist_dir).relative_to(root / CHAT_MEMORY_PERSIST_DIR)
		return str(mem_id)

	def is_chat_group_memory(self) -> bool:
		r"""
		Whether this class records the history of a chat group or not.
		"""
		try:
			self.vector_index.docstore.get_node(CHAT_GROUP_MEMBERS_NODE_NAME)
			return True
		except ValueError as e:
			return False

	@classmethod
	def from_memory_id(
		cls,
		memory_id: str,
		embed_model: BaseEmbedding,
		retriever_kwargs: dict,
		description: str = None,
		group_members: Optional[List[str]] = None,
	):
		r"""
		Construct from the memory_id.
		If the corresponding persist_dir of the memory_id does not exist, a new ChatMemory will be created.

		Args:
			memory_id (str): a user_id of a lab member or a chat_group_id.
			embed_model (BaseEmbedding): The used embedding model.
			retriever_kwargs (dict): Not used.
			description (str): The description of this ChatMemory.
			group_members (Optional[List[str]]): If the memory_id is a chat_group_id, the group members must be given.

		Returns:
			ChatVectorMemory
		"""
		account_manager = AccountManager()

		if memory_id not in account_manager.get_users() + account_manager.get_chat_groups():
			raise ValueError(f"Invalid user id or chat group id: {memory_id}.")

		root = Path(__file__)
		for idx in range(5):
			root = root.parent

		persist_dir = str(root / f"{CHAT_MEMORY_PERSIST_DIR}/{memory_id}")
		fs = fsspec.filesystem("file")
		if fs.exists(persist_dir):
			return cls.from_storage(
				persist_dir=persist_dir,
				embed_model=embed_model,
				retriever_kwargs=retriever_kwargs,
			)

		date, h_m_s = get_time()
		init_msg = ChatMessage(
			role=MessageRole.SYSTEM,
			content=f"This Memory Index is used for storing the chat history related to the USER/CHAT GROUP: {memory_id}\n"
					f"Description: {description}.",
			additional_kwargs={
				LOG_DATE_NAME: date,
				LOG_TIME_NAME: h_m_s,
			},
		)
		text_node = _get_starter_node_for_new_batch()
		text_node.id_ = MEMORY_FIRST_NODE_NAME
		text_node.text += init_msg.content
		text_node.metadata[LOG_DATE_NAME] = [init_msg.additional_kwargs[LOG_DATE_NAME],]
		text_node.metadata[LOG_TIME_NAME] = [init_msg.additional_kwargs[LOG_TIME_NAME],]

		last_id_info_node = TextNode(text=text_node.node_id, id_=MEMORY_LAST_NODE_ID_NAME)

		nodes = [text_node, last_id_info_node]
		if group_members is not None:
			for user_id in group_members:
				try:
					account_manager.check_valid_user(user_id=user_id)
				except ValueError as e:
					return f"Error: {e!s}"
			members_node = TextNode(text=",".join(group_members))
			members_node.id_ = CHAT_GROUP_MEMBERS_NODE_NAME
			nodes.append(members_node)

		vector_index = VectorStoreIndex(
			nodes=nodes,
			embed_model=embed_model,
		)
		return cls(
			vector_index=vector_index,
			persist_dir=persist_dir,
			retriever_kwargs=retriever_kwargs,
		)

	def update_node(self, node_id: str, node: BaseNode):
		r"""
		Update a node in the vector index.

		Args:
			node_id (str): The node_id of the node to be updated.
			node (BaseNode): The new node.
		"""
		self.vector_index.delete_nodes([node_id])
		self.vector_index.insert_nodes([node])

	def put(self, message: ChatMessage) -> None:
		"""
		Put chat history.

		Metadata: `LOG_DATE_NAME`: [date, ]; `LOG_TIME_NAME`: [time, ]

		The node_id of the Last Text Node is stored in the node `MEMORY_LAST_NODE_ID_NAME`
		Every time a New Text Node is put in, execute:

		- Last Text Node -> next_node = New Text Node
		- New Text Node -> prev_node = Last Text Node
		- let New Text Node be the Last Text Node

		Args:
			message (ChatMessage): a chat message.
		"""
		if not self.batch_by_user_message or message.role in [MessageRole.USER, MessageRole.SYSTEM, ]:
			# if not batching by user message, commit to vector store immediately after adding
			self.cur_batch_textnode = _get_starter_node_for_new_batch()
			# add date and time
			self.cur_batch_textnode.metadata[LOG_DATE_NAME] = [message.additional_kwargs[LOG_DATE_NAME],]
			self.cur_batch_textnode.metadata[LOG_TIME_NAME] = [message.additional_kwargs[LOG_TIME_NAME],]
			# add previous and next relationships.
			last_info_node = self.vector_index.docstore.get_node(MEMORY_LAST_NODE_ID_NAME)
			last_node_id = last_info_node.text
			last_node = self.vector_index.docstore.get_node(last_node_id)
			last_node.relationships[NodeRelationship.NEXT] = RelatedNodeInfo(
				node_id=self.cur_batch_textnode.node_id
			)
			self.cur_batch_textnode.relationships[NodeRelationship.PREVIOUS] = RelatedNodeInfo(
				node_id=last_node.node_id
			)
			# update last node id
			last_info_node.set_content(self.cur_batch_textnode.node_id)
			self.update_node(node_id=last_node_id, node=last_node)
			self.update_node(node_id=MEMORY_LAST_NODE_ID_NAME, node=last_info_node)

		# update current batch textnode
		sub_dict = _stringify_chat_message(message)
		role = sub_dict["role"]
		content = sub_dict["content"] or ""
		new_msg = (
			f">>> {role} message:\n"
			f"{content.strip()}\n"
		)
		self.cur_batch_textnode.text += new_msg
		# self.cur_batch_textnode.metadata["sub_dicts"].append(sub_dict)
		self._commit_node(override_last=True)

	def persist(self, persist_dir: str = None):
		persist_dir = persist_dir or self.persist_dir
		fs = fsspec.filesystem("file")
		if not fs.exists(persist_dir):
			fs.makedirs(persist_dir)
		self.vector_index.storage_context.persist(persist_dir=persist_dir)


def update_chat_memory(
	memory_id: str,
	chat_messages: List[ChatMessage],
	embed_model: BaseEmbedding = None
):
	r"""
	Update the user/chat_group specific chat memory.

	Args:
		memory_id (str): user_id or chat_group_id
		chat_messages (List[ChatMessage]): New chat messages.
		embed_model (BaseEmbedding): The used embedding model.

	Returns:
		None or an Error string.
	"""
	chat_memory = ChatVectorMemory.from_memory_id(
		memory_id=memory_id,
		embed_model=embed_model or Settings.embed_model,
		retriever_kwargs={},
	)

	if not isinstance(chat_memory, ChatVectorMemory):
		return chat_memory

	for msg in chat_messages:
		chat_memory.put(msg)

	chat_memory.persist()


if __name__ == "__main__":
	llm , embed_model = get_models()

	root = Path(__file__)
	for idx in range(5):
		root = root.parent

	chat_memory = ChatVectorMemory.from_storage(
		persist_dir=str(root / f"{CHAT_MEMORY_PERSIST_DIR}/杨再正"),
		embed_model=embed_model,
		retriever_kwargs={},
	)
	print(chat_memory.vector_index.docstore.docs)

	last_info_node = chat_memory.vector_index.docstore.get_node(MEMORY_LAST_NODE_ID_NAME)
	last_node_id = last_info_node.text
	last_node = chat_memory.vector_index.docstore.get_node(last_node_id)

	print("Last node: ", last_node.get_content(metadata_mode=MetadataMode.LLM))
	print("Meta data: \n", last_node.metadata)
	prev_id = last_node.prev_node.node_id
	prev_node = chat_memory.vector_index.docstore.get_node(prev_id)
	print("previous: \n", prev_node.get_content(metadata_mode=MetadataMode.LLM))

	prev_next_id = prev_node.next_node.node_id
	prev_next_node = chat_memory.vector_index.docstore.get_node(prev_next_id)
	print("pre-next: \n", prev_next_node.get_content(metadata_mode=MetadataMode.LLM))
