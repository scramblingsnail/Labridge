import llama_index.core.instrumentation as instrument
import datetime

from llama_index.core.agent.react.output_parser import ReActOutputParser
from llama_index.core.agent.runner.base import AgentRunner
from llama_index.core.memory.chat_memory_buffer import ChatMemoryBuffer
from llama_index.core.agent.react.formatter import ReActChatFormatter
from llama_index.core.objects.base import ObjectRetriever
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.callbacks import CallbackManager
from llama_index.core.memory.types import BaseMemory
from llama_index.core.tools.types import BaseTool
from llama_index.core.settings import Settings
from llama_index.core.utils import print_text
from llama_index.core.tools import ToolOutput
from llama_index.core.llms.llm import LLM
from llama_index.core.chat_engine.types import AgentChatResponse
from llama_index.core.instrumentation.events.agent import (
    AgentChatWithStepStartEvent,
    AgentChatWithStepEndEvent,
)
from llama_index.core.chat_engine.types import (
    AGENT_CHAT_RESPONSE_TYPE,
    ChatResponseMode,
)

from llama_index.core.memory.vector_memory import _stringify_chat_message

from typing import (
    Sequence,
    Callable,
	Optional,
	List,
	Union,
	Type,
	Any,
	Tuple,
)

from .react_step import InstructReActAgentWorker
from labridge.accounts.users import AccountManager
from labridge.common.chat.utils import unpack_user_message


dispatcher = instrument.get_dispatcher(__name__)


class InstructReActAgent(AgentRunner):
	def __init__(
		self,
		tools: Sequence[BaseTool],
		llm: LLM,
		memory: BaseMemory,
		max_iterations: int = 10,
		react_chat_formatter: Optional[ReActChatFormatter] = None,
		output_parser: Optional[ReActOutputParser] = None,
		callback_manager: Optional[CallbackManager] = None,
		verbose: bool = False,
		tool_retriever: Optional[ObjectRetriever[BaseTool]] = None,
		handle_reasoning_failure_fn: Optional[Callable[[CallbackManager, Exception],
		ToolOutput]] = None,
		enable_instruct: bool = False,
		enable_comment: bool = False,
	):
		self.user_id_list = AccountManager().get_users()
		self.chat_group_list = AccountManager().get_chat_groups()
		step_engine = InstructReActAgentWorker.from_tools(
			tools=tools,
			tool_retriever=tool_retriever,
			user_id_list=self.user_id_list,
			chat_group_id_list=self.chat_group_list,
			llm=llm,
			max_iterations=max_iterations,
			react_chat_formatter=react_chat_formatter,
			output_parser=output_parser,
			callback_manager=callback_manager,
			verbose=verbose,
			handle_reasoning_failure_fn=handle_reasoning_failure_fn,
			enable_instruct=enable_instruct,
		)
		self._enable_comment = enable_comment
		super().__init__(
			step_engine,
			memory=memory,
			llm=llm,
			callback_manager=callback_manager,
		)

	def update_user_id_list(self):
		self.user_id_list = AccountManager().get_users()
		self.agent_worker.user_id_list = self.user_id_list

	def set_enable_instruct(self, enable: bool):
		self.agent_worker.set_enable_instruct(enable)

	def set_enable_comment(self, enable: bool):
		self._enable_comment = enable

	@property
	def enable_instruct(self):
		return self.agent_worker.enable_instruct

	@property
	def enable_comment(self):
		return self._enable_comment

	@dispatcher.span
	def _chat(self, message: str, chat_history: Optional[List[ChatMessage]] = None,
		tool_choice: Union[str, dict] = "auto",
		mode: ChatResponseMode = ChatResponseMode.WAIT, ) -> AGENT_CHAT_RESPONSE_TYPE:
		"""
		Chat with step executor.

		Assert the message is as the following format:
		**User id:** XXX
		**Query:** XXX
		"""
		if chat_history is not None:
			self.memory.set(chat_history)

		user_id, chat_group_id, chat_message = unpack_user_message(message_str=message)
		task = self.create_task(chat_message)
		task.extra_state["user_id"] = user_id
		if chat_group_id is not None:
			task.extra_state["chat_group_id"] = chat_group_id

		result_output = None
		dispatcher.event(AgentChatWithStepStartEvent(user_msg=chat_message))

		# 显式获取 initial step
		step = self.state.get_step_queue(task.task_id).popleft()

		while True:
			# pass step queue in as argument, assume step executor is stateless
			# Ask User
			# get step
			cur_step_output = self._run_step(task.task_id, step=step, mode=mode, tool_choice=tool_choice)

			if cur_step_output.is_last:
				result_output = cur_step_output
				break

			step_queue = self.state.get_step_queue(task.task_id)
			step = step_queue.popleft()

			# Send the reasoning to the user.
			if self.enable_instruct:
				# TODO: 将 cur_step_output.output.response 输出给 User, 获取 User 的 Instruction。
				print_text(text=cur_step_output.output.response, color="llama_turquoise", end="\n")
				# TODO: 获取下一步 step, 并将Instruction作为 step.input。
				comment = input("User Comment: ")
				print_text(f">>> User's comment: \n {comment}", color="blue", end="\n")

			# ensure tool_choice does not cause endless loops
			tool_choice = "auto"

		# TODO: use the ChatVectorMemory to record the long-term chat history (including tool logs.)

		result = self.finalize_response(task.task_id, result_output, )
		# add the tool log if necessary.
		result.response += "\n\n".join([""] + task.extra_state["tool_log"])

		# for msg in self.memory.get_all():
		# 	# update current batch textnode
		# 	sub_dict = _stringify_chat_message(msg)
		# 	print(sub_dict)

		dispatcher.event(AgentChatWithStepEndEvent(response=result))
		return result

	@dispatcher.span
	async def _achat(self, message: str, chat_history: Optional[List[ChatMessage]] = None,
		tool_choice: Union[str, dict] = "auto",
		mode: ChatResponseMode = ChatResponseMode.WAIT, ) -> AGENT_CHAT_RESPONSE_TYPE:
		"""Chat with step executor."""
		if chat_history is not None:
			self.memory.set(chat_history)
		task = self.create_task(message)

		result_output = None
		dispatcher.event(AgentChatWithStepStartEvent(user_msg=message))

		# 显式获取 initial step
		step = self.state.get_step_queue(task.task_id).popleft()
		while True:
			# pass step queue in as argument, assume step executor is stateless
			cur_step_output = await self._run_step(task.task_id, step=step, mode=mode, tool_choice=tool_choice)

			if cur_step_output.is_last:
				result_output = cur_step_output
				break

			step_queue = self.state.get_step_queue(task.task_id)
			step = step_queue.popleft()

			# ensure tool_choice does not cause endless loops
			tool_choice = "auto"

		result = self.finalize_response(task.task_id, result_output, )
		result.response += "\n\n".join([""] + task.extra_state["tool_log"])
		dispatcher.event(AgentChatWithStepEndEvent(response=result))
		return result

	@classmethod
	def from_tools(
		cls,
		tools: Optional[List[BaseTool]] = None,
		tool_retriever: Optional[ObjectRetriever[BaseTool]] = None,
		llm: Optional[LLM] = None,
		chat_history: Optional[List[ChatMessage]] = None,
		memory: Optional[BaseMemory] = None,
		memory_cls: Type[BaseMemory] = ChatMemoryBuffer,
		max_iterations: int = 10,
		react_chat_formatter: Optional[ReActChatFormatter] = None,
		output_parser: Optional[ReActOutputParser] = None,
		callback_manager: Optional[CallbackManager] = None,
		verbose: bool = False,
		handle_reasoning_failure_fn: Optional[Callable[[CallbackManager, Exception], ToolOutput]] = None,
		enable_instruct: bool = False,
		enable_comment: bool = False,
		**kwargs: Any,
	) -> "InstructReActAgent":
		"""
		Convenience constructor method from set of BaseTools (Optional).

		NOTE: kwargs should have been exhausted by this point. In other words
		the various upstream components such as BaseSynthesizer (response synthesizer)
		or BaseRetriever should have picked up off their respective kwargs in their
		constructions.

		If `handle_reasoning_failure_fn` is provided, when LLM fails to follow the response templates specified in
		the System Prompt, this function will be called. This function should provide to the Agent, so that the Agent
		can have a second chance to fix its mistakes.
		To handle the exception yourself, you can provide a function that raises the `Exception`.

		Note: If you modified any response template in the System Prompt, you should override the method
		`_extract_reasoning_step` in `ReActAgentWorker`.

		Returns:
			InstructReActAgent
		"""
		llm = llm or Settings.llm
		if callback_manager is not None:
			llm.callback_manager = callback_manager
		memory = memory or memory_cls.from_defaults(chat_history=chat_history or [], llm=llm)
		return cls(
			tools=tools or [],
			tool_retriever=tool_retriever,
			llm=llm,
			memory=memory,
			max_iterations=max_iterations,
			react_chat_formatter=react_chat_formatter,
			output_parser=output_parser,
			callback_manager=callback_manager,
			verbose=verbose,
			handle_reasoning_failure_fn=handle_reasoning_failure_fn,
			enable_instruct=enable_instruct,
			enable_comment=enable_comment,
		)

	def set_user(self, user_id: str):
		# TODO: save chat histories.
		self.user_id = user_id
		self.agent_worker.user_id = user_id
