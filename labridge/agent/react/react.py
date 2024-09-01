import llama_index.core.instrumentation as instrument

from llama_index.core.agent.react.output_parser import ReActOutputParser
from llama_index.core.memory.chat_memory_buffer import ChatMemoryBuffer
from llama_index.core.agent.react.formatter import ReActChatFormatter
from llama_index.core.agent.runner.base import AgentRunner
from llama_index.core.agent.react import ReActAgent
from llama_index.core.objects.base import ObjectRetriever
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.callbacks import CallbackManager
from llama_index.core.memory.types import BaseMemory
from llama_index.core.tools.types import BaseTool
from llama_index.core.settings import Settings
from llama_index.core.utils import print_text
from llama_index.core.tools import ToolOutput
from llama_index.core.agent.types import Task
from llama_index.core.llms.llm import LLM
from llama_index.core.instrumentation.events.agent import (
    AgentChatWithStepStartEvent,
    AgentChatWithStepEndEvent,
)
from llama_index.core.chat_engine.types import (
    AGENT_CHAT_RESPONSE_TYPE,
    ChatResponseMode,
)

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

from labridge.accounts.users import AccountManager
from labridge.tools.utils import (
	get_all_system_logs,
	get_extra_str_to_user,
	get_ref_file_paths,
)
from labridge.agent.chat_msg.msg_types import PackedUserMessage
from labridge.agent.chat_msg.msg_types import ChatBuffer

from .react_step import InstructReActAgentWorker, update_intervene_status


dispatcher = instrument.get_dispatcher(__name__)


class InstructReActAgent(AgentRunner):
	r"""
	This Agent uses the Reasoning and acting prompt framework.
	Additionally, this class enables the user to intervene the reasoning phase and acting phase:

	- If `enable_instruct` is set to True, in the reasoning phase, the user is able to instruct the agent's thought.
	- If 'enable_comment' is set to True, in the reacting phase, the user is able to comment the agent's action, the
	user's comment will be treated as observation to instruct the agent's next thought.

	Args:
		tools (Sequence[BaseTool]): The available tools of the agent.
		llm (LLM): The used LLM.
		memory (BaseMemory): The short-term memory.
		max_iterations (int): The maximum reasoning-acting steps.
		react_chat_formatter (Optional[ReActChatFormatter]): The ReAct prompt template.
		output_parser (Optional[ReActOutputParser]): Used to parse tool call from the agent's Acting output.
		callback_manager (Optional[CallbackManager]):
		verbose (bool): Whether to show the inner Reasoning-Acting process.
		tool_retriever (Optional[ObjectRetriever[BaseTool]]): Used to retrieve proper tool among the given tools.
		handle_reasoning_failure_fn (Optional[Callable[[CallbackManager, Exception], ToolOutput]]):
		enable_instruct (bool): Whether to enable user's instructing in the reasoning phase.
		enable_comment (bool): Whether to enable user's commenting in the acting phase.
	"""
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
		r""" Update the registered user ids """
		self.user_id_list = AccountManager().get_users()
		self.agent_worker.user_id_list = self.user_id_list

	def set_enable_instruct(self, enable: bool):
		r""" Set enable_instruct. """
		self.agent_worker.set_enable_instruct(enable)

	def set_enable_comment(self, enable: bool):
		r""" Set enable_comment. """
		self._enable_comment = enable

	@property
	def enable_instruct(self):
		r""" Enable user's instruction in Reasoning Phase. """
		return self.agent_worker.enable_instruct

	@property
	def enable_comment(self):
		r""" Enable user's instruction in Acting Phase. """
		return self._enable_comment

	def final_process_tool_logs(self, task: Task) -> Tuple[str, List[str]]:
		r"""
		Process the tool logs of the agent's acting.

		1. Record the log_to_system: log_to_system will be recorded to the long-term memory.
		2. Extract the log_to_user: log_to_user will be attached to the agent's answer.
		3. Extract the references: references are the file paths of the relevant documents. This information will be
		sent to the frontend.
		"""
		tool_log_list = task.extra_state["tool_log"]
		tool_logs_str = get_all_system_logs(tool_logs=tool_log_list)

		# task.extra_state["new_memory"].put(
		# 	ChatMessage(
		# 		content=tool_logs_str,
		# 		role=MessageRole.TOOL,
		# 	)
		# )
		to_user_logs = get_extra_str_to_user(tool_logs=tool_log_list)
		ref_file_paths = get_ref_file_paths(tool_logs=tool_log_list)
		return to_user_logs, ref_file_paths

	@dispatcher.span
	def _chat(self, message: str, chat_history: Optional[List[ChatMessage]] = None,
		tool_choice: Union[str, dict] = "auto",
		mode: ChatResponseMode = ChatResponseMode.WAIT, ) -> AGENT_CHAT_RESPONSE_TYPE:
		"""
		Chat with step executor.
		User is able to instruct or comment.
		"""
		if chat_history is not None:
			self.memory.set(chat_history)

		packed_msgs = PackedUserMessage.loads(dumped_str=message)
		user_id, chat_group_id = packed_msgs.user_id, packed_msgs.chat_group_id
		user_msg, system_msg = packed_msgs.user_msg, packed_msgs.system_msg

		task = self.create_task(
			input=user_msg,
			extra_state={
				"system_msg": system_msg,
				"user_id": user_id,
				"enable_instruct": ChatBuffer.config_buffer[user_id].enable_instruct,
				"enable_comment": ChatBuffer.config_buffer[user_id].enable_comment,
			}
		)
		if chat_group_id is not None:
			task.extra_state["chat_group_id"] = chat_group_id

		result_output = None
		dispatcher.event(AgentChatWithStepStartEvent(user_msg=user_msg))

		# 显式获取 initial step
		step = self.state.get_step_queue(task.task_id).popleft()

		while True:
			# pass step queue in as argument, assume step executor is stateless
			cur_step_output = self._run_step(
				task.task_id,
				step=step,
				mode=mode,
				tool_choice=tool_choice,
			)

			if cur_step_output.is_last:
				result_output = cur_step_output
				break

			step_queue = self.state.get_step_queue(task.task_id)
			step = step_queue.popleft()

			# Send the observation to the user.
			if task.extra_state["enable_comment"]:
				# TODO: 将 cur_step_output.output.response 输出给 User, 获取 User 的 Instruction。
				print_text(text=cur_step_output.output.response, color="llama_turquoise", end="\n")
				# TODO: 获取下一步 step, 并将Instruction作为 step.input。
				packed_msgs = ChatBuffer.test_get_user_text(
					user_id=user_id,
					enable_instruct=False,
					enable_comment=False,
				)

				user_comment = packed_msgs.user_msg
				system_msg = packed_msgs.system_msg
				update_intervene_status(
					task=task,
					enable_instruct=ChatBuffer.config_buffer[user_id].enable_instruct,
					enable_comment=ChatBuffer.config_buffer[user_id].enable_comment,
					reply_in_speech=ChatBuffer.config_buffer[user_id].reply_in_speech,
				)
				# Add as the step's input
				step.input = user_comment
				step.step_state["system_msg"] = system_msg
				print_text(f">>> User's comment: \n {user_comment}", color="blue", end="\n")

			# ensure tool_choice does not cause endless loops
			tool_choice = "auto"

		to_user_logs, ref_file_paths = self.final_process_tool_logs(task=task)
		result = self.finalize_response(task.task_id, result_output, )
		# add the tool log if necessary.
		result.response += f"\n\n{to_user_logs}"
		dispatcher.event(AgentChatWithStepEndEvent(response=result))

		if result.metadata is None:
			result.metadata = {"references": ref_file_paths}
		else:
			result.metadata.update({"references": ref_file_paths})
		return result

	@dispatcher.span
	async def _achat(self, message: str, chat_history: Optional[List[ChatMessage]] = None,
		tool_choice: Union[str, dict] = "auto",
		mode: ChatResponseMode = ChatResponseMode.WAIT, ) -> AGENT_CHAT_RESPONSE_TYPE:
		"""
		Async version.
		Chat with step executor.
		User is able to instruct or comment.
		"""
		if chat_history is not None:
			self.memory.set(chat_history)

		packed_msgs = PackedUserMessage.loads(dumped_str=message)
		user_id, chat_group_id = packed_msgs.user_id, packed_msgs.chat_group_id
		user_msg, system_msg = packed_msgs.user_msg, packed_msgs.system_msg

		task = self.create_task(
			input=user_msg,
			extra_state={
				"system_msg": system_msg,
				"user_id": user_id,
				"enable_instruct": ChatBuffer.config_buffer[user_id].enable_instruct,
				"enable_comment": ChatBuffer.config_buffer[user_id].enable_comment,
				"reply_in_speech": ChatBuffer.config_buffer[user_id].reply_in_speech,
			}
		)
		if chat_group_id is not None:
			task.extra_state["chat_group_id"] = chat_group_id

		result_output = None
		dispatcher.event(AgentChatWithStepStartEvent(user_msg=user_msg))

		# explicitly get initial step
		step = self.state.get_step_queue(task.task_id).popleft()
		while True:
			# pass step queue in as argument, assume step executor is stateless
			cur_step_output = await self._arun_step(
				task.task_id,
				step=step,
				mode=mode,
				tool_choice=tool_choice,
			)

			if cur_step_output.is_last:
				result_output = cur_step_output
				break

			step_queue = self.state.get_step_queue(task.task_id)
			step = step_queue.popleft()

			# Send the observation to the user.
			if task.extra_state["enable_comment"]:
				# TODO: 将 cur_step_output.output.response 输出给 User, 获取 User 的 Instruction。
				ChatBuffer.put_agent_reply(
					user_id=user_id,
					reply_str=cur_step_output.output.response,
					inner_chat=True,
				)
				# TODO: 将Instruction作为 step.input, 以及将 system_msg 记入 step.extra_state。
				packed_msgs = await ChatBuffer.get_user_msg(user_id=user_id)
				user_comment, system_msg = packed_msgs.user_msg, packed_msgs.system_msg
				# update
				update_intervene_status(
					task=task,
					enable_instruct=ChatBuffer.config_buffer[user_id].enable_instruct,
					enable_comment=ChatBuffer.config_buffer[user_id].enable_comment,
					reply_in_speech=ChatBuffer.config_buffer[user_id].reply_in_speech,
				)
				# add to the step's input
				step.input = user_comment
				step.step_state["system_msg"] = system_msg
				print_text(
					f"System: {system_msg}"
					f">>> User's comment: \n {user_comment}",
					color="blue",
					end="\n",
				)

			# ensure tool_choice does not cause endless loops
			tool_choice = "auto"

		to_user_logs, ref_file_paths = self.final_process_tool_logs(task=task)
		result = self.finalize_response(task.task_id, result_output, )
		result.response += f"\n\n{to_user_logs}"
		dispatcher.event(AgentChatWithStepEndEvent(response=result))
		if result.metadata is None:
			result.metadata = {"references": ref_file_paths}
		else:
			result.metadata.update({"references": ref_file_paths})
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
