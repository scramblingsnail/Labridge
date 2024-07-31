import llama_index.core.instrumentation as instrument
import uuid

from llama_index.core.agent.react.step import (
	ReActAgentWorker,
)

from llama_index.core.memory.chat_memory_buffer import ChatMemoryBuffer

from .react_chat_format import InstructChatFormatter

from typing import (
    Any,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    cast,
    Callable,
)

from llama_index.core.agent.react.formatter import ReActChatFormatter
from llama_index.core.agent.react.output_parser import ReActOutputParser
from llama_index.core.agent.react.types import (
    ActionReasoningStep,
    BaseReasoningStep,
    ObservationReasoningStep,
)
from llama_index.core.agent.types import (
    Task,
    TaskStep,
    TaskStepOutput,
)
from llama_index.core.base.llms.types import MessageRole
from llama_index.core.callbacks import (
    CallbackManager,
    CBEventType,
    EventPayload,
)
from llama_index.core.base.llms.types import ChatMessage, ChatResponse
from llama_index.core.llms.llm import LLM
from llama_index.core.objects.base import ObjectRetriever
from llama_index.core.settings import Settings
from llama_index.core.tools import BaseTool, ToolOutput
from llama_index.core.tools.types import AsyncBaseTool
from llama_index.core.utils import print_text
from llama_index.core.memory.types import BaseMemory

from labridge.paper.query_engine.paper_query_engine import PAPER_QUERY_TOOL_NAME
from labridge.memory.chat_memory import CHAT_DATE_NAME, CHAT_TIME_NAME
from labridge.accounts.users import AccountManager
from labridge.memory.chat_memory import update_chat_memory
from .utils import get_time

from labridge.tools.utils import unpack_tool_output

dispatcher = instrument.get_dispatcher(__name__)


# The tools whose log should be sent to the user.
OUTPUT_LOG_TOOLS = [
	PAPER_QUERY_TOOL_NAME,
]


def add_user_step_to_reasoning(
    step: TaskStep,
    memory: BaseMemory,
    current_reasoning: List[BaseReasoningStep],
    verbose: bool = False,
) -> None:
	"""Add user step to memory."""
	if "is_first" in step.step_state and step.step_state["is_first"]:
		# add to new memory
		record_str = step.input
		date, h_m_s = get_time()
		additional_kwargs = {
			CHAT_DATE_NAME: date,
			CHAT_TIME_NAME: h_m_s,
		}
		memory.put(
			ChatMessage(
				content=record_str,
				role=MessageRole.USER,
				additional_kwargs=additional_kwargs,
			)
		)
		step.step_state["is_first"] = False
	else:
		reasoning_step = ObservationReasoningStep(observation=step.input)
		current_reasoning.append(reasoning_step)
		if verbose:
			print(f"Added user message to memory: {step.input}")


class InstructReActAgentWorker(ReActAgentWorker):
	def __init__(
		self,
		tools: Sequence[BaseTool],
		llm: LLM,
		user_id_list: List[str],
		chat_group_id_list: List[str],
		max_iterations: int = 10,
		react_chat_formatter: Optional[ReActChatFormatter] = None,
		output_parser: Optional[ReActOutputParser] = None,
		callback_manager: Optional[CallbackManager] = None,
		verbose: bool = False,
		tool_retriever: Optional[ObjectRetriever[BaseTool]] = None,
		handle_reasoning_failure_fn: Optional[Callable[[CallbackManager, Exception], ToolOutput]] = None,
		enable_instruct: bool = False,
	):
		self._enable_instruct = enable_instruct
		self._instruct_chat_formatter = InstructChatFormatter()
		self.user_id_list = user_id_list
		self.chat_group_id_list = chat_group_id_list
		super().__init__(
			tools=tools,
			llm=llm,
			max_iterations=max_iterations,
			react_chat_formatter=react_chat_formatter,
			output_parser=output_parser,
			callback_manager=callback_manager,
			verbose=verbose,
			tool_retriever=tool_retriever,
			handle_reasoning_failure_fn=handle_reasoning_failure_fn,
		)

	def set_enable_instruct(self, enable: bool):
		self._enable_instruct = enable

	@property
	def enable_instruct(self):
		return self._enable_instruct

	@classmethod
	def from_tools(
		cls,
		tools: Optional[Sequence[BaseTool]] = None,
		tool_retriever: Optional[ObjectRetriever[BaseTool]] = None,
		llm: Optional[LLM] = None,
		user_id_list: List[str] = None,
		chat_group_id_list: List[str] = None,
		max_iterations: int = 10,
		react_chat_formatter: Optional[ReActChatFormatter] = None,
		output_parser: Optional[ReActOutputParser] = None,
		callback_manager: Optional[CallbackManager] = None,
		verbose: bool = False,
		handle_reasoning_failure_fn: Optional[Callable[[CallbackManager, Exception], ToolOutput]] = None,
		enable_instruct: bool = False,
		**kwargs: Any,
	) -> "InstructReActAgentWorker":
		"""Convenience constructor method from set of BaseTools (Optional).

		NOTE: kwargs should have been exhausted by this point. In other words
		the various upstream components such as BaseSynthesizer (response synthesizer)
		or BaseRetriever should have picked up off their respective kwargs in their
		constructions.

		Returns:
			ReActAgentWorker
		"""
		llm = llm or Settings.llm
		if callback_manager is not None:
			llm.callback_manager = callback_manager
		return cls(
			tools=tools or [],
			tool_retriever=tool_retriever,
			user_id_list=user_id_list or AccountManager().get_users(),
			chat_group_id_list=chat_group_id_list or AccountManager().get_chat_groups(),
			llm=llm,
			max_iterations=max_iterations,
			react_chat_formatter=react_chat_formatter,
			output_parser=output_parser,
			callback_manager=callback_manager,
			verbose=verbose,
			handle_reasoning_failure_fn=handle_reasoning_failure_fn,
			enable_instruct=enable_instruct,
		)

	def initialize_step(self, task: Task, **kwargs: Any) -> TaskStep:
		"""Initialize step from task."""
		sources: List[ToolOutput] = []
		current_reasoning: List[BaseReasoningStep] = []
		# temporary memory for new messages
		new_memory = ChatMemoryBuffer.from_defaults()
		# the tool log that are supposed to be added to the final response.
		tool_log = []

		# initialize task state
		task_state = {
			"sources": sources,
			"current_reasoning": current_reasoning,
			"new_memory": new_memory,
			"tool_log": tool_log,
		}
		task.extra_state.update(task_state)

		return TaskStep(
			task_id=task.task_id,
			step_id=str(uuid.uuid4()),
			input=task.input,
			step_state={"is_first": True},
		)

	def _run_step(self, step: TaskStep, task: Task, ) -> TaskStepOutput:
		"""Run step."""
		if step.input is not None:
			step.step_state["user_id"] = task.extra_state["user_id"]
			add_user_step_to_reasoning(
				step,
				task.extra_state["new_memory"],
				task.extra_state["current_reasoning"],
				verbose=self._verbose,
			)
		tools = self.get_tools(task.input)
		input_chat = self._react_chat_formatter.format(
			tools,
			chat_history=task.memory.get(input=task.input) + task.extra_state["new_memory"].get_all(),
			current_reasoning=task.extra_state["current_reasoning"],
		)

		# send prompt
		chat_response = self._llm.chat(input_chat)

		if self._enable_instruct:
			# TODO: interface: Send the action to the user
			print_text(f">>> Initial reasoning: \n{chat_response.message.content}", color="pink", end="\n")
			# TODO: interface: Get the user's suggestion
			user_advice = input("User suggest: ")
			print_text(f">>> User's suggestion: \n{user_advice}", color="blue", end="\n")
			reasoning_step = ObservationReasoningStep(observation=f"User's suggestion: {user_advice}")
			task.extra_state["current_reasoning"].append(reasoning_step)

			instruct_chat = self._instruct_chat_formatter.format(
				tools,
				chat_history=task.memory.get(input=task.input) + task.extra_state["new_memory"].get_all(),
				current_reasoning=task.extra_state["current_reasoning"],
				prev_response=chat_response.message.content,
				suggestion=f"User's suggestion: {user_advice}",
			)
			chat_response = self._llm.chat(instruct_chat)
			print_text(f">>> Modified reasoning: \n{chat_response.message.content}", color="green", end="\n")

		# given react prompt outputs, call tools or return response
		reasoning_steps, is_done = self._process_actions(task, tools, output=chat_response)
		task.extra_state["current_reasoning"].extend(reasoning_steps)
		agent_response = self._get_response(task.extra_state["current_reasoning"], task.extra_state["sources"])
		if is_done:
			date, h_m_s = get_time()
			additional_kwargs = {
				CHAT_DATE_NAME: date,
				CHAT_TIME_NAME: h_m_s,
			}
			task.extra_state["new_memory"].put(
				ChatMessage(
					content=agent_response.response,
					role=MessageRole.ASSISTANT,
					additional_kwargs=additional_kwargs,
				)
			)

		return self._get_task_step_response(agent_response, step, is_done)

	async def _arun_step(self, step: TaskStep, task: Task, ) -> TaskStepOutput:
		"""Run step."""
		if step.input is not None:
			step.step_state["user_id"] = task.extra_state["user_id"]
			add_user_step_to_reasoning(step, task.extra_state["new_memory"], task.extra_state["current_reasoning"],
				verbose=self._verbose, )
		# TODO: see if we want to do step-based inputs
		tools = self.get_tools(task.input)

		input_chat = self._react_chat_formatter.format(
			tools,
			chat_history=task.memory.get(input=task.input) + task.extra_state["new_memory"].get_all(),
			current_reasoning=task.extra_state["current_reasoning"],
		)

		# send prompt
		chat_response = await self._llm.achat(input_chat)

		if self._enable_instruct:
			# TODO: interface: Send the action to the user
			print_text(f">>> Initial reasoning: \n{chat_response.message.content}", color="pink", end="\n")
			# TODO: interface: Get the user's suggestion
			user_advice = input("User suggest: ")
			print_text(f">>> User's suggestion: \n{user_advice}", color="blue", end="\n")
			reasoning_step = ObservationReasoningStep(observation=f"User's suggestion: {user_advice}")
			task.extra_state["current_reasoning"].append(reasoning_step)

			instruct_chat = self._instruct_chat_formatter.format(
				tools,
				chat_history=task.memory.get(input=task.input) + task.extra_state["new_memory"].get_all(),
				current_reasoning=task.extra_state["current_reasoning"],
				prev_response=chat_response.message.content,
				suggestion=f"User's suggestion: {user_advice}",
			)
			chat_response = await self._llm.achat(instruct_chat)
			print_text(f">>> Modified reasoning: \n{chat_response.message.content}", color="green", end="\n")

		# given react prompt outputs, call tools or return response
		reasoning_steps, is_done = await self._aprocess_actions(task, tools, output=chat_response)
		task.extra_state["current_reasoning"].extend(reasoning_steps)
		agent_response = self._get_response(task.extra_state["current_reasoning"], task.extra_state["sources"])
		if is_done:
			date, h_m_s = get_time()
			additional_kwargs = {
				CHAT_DATE_NAME: date,
				CHAT_TIME_NAME: h_m_s,
			}
			task.extra_state["new_memory"].put(
				ChatMessage(
					content=agent_response.response,
					role=MessageRole.ASSISTANT,
					additional_kwargs=additional_kwargs,
				)
			)

		return self._get_task_step_response(agent_response, step, is_done)

	def _process_actions(
		self,
		task: Task,
		tools: Sequence[AsyncBaseTool],
		output: ChatResponse,
		is_streaming: bool = False,
	) -> Tuple[List[BaseReasoningStep], bool]:
		tools_dict: Dict[str, AsyncBaseTool] = {tool.metadata.get_name(): tool for tool in tools}
		tool = None

		try:
			_, current_reasoning, is_done = self._extract_reasoning_step(output, is_streaming)
		except ValueError as exp:
			current_reasoning = []
			tool_output = self._handle_reasoning_failure_fn(self.callback_manager, exp)
		else:
			if is_done:
				return current_reasoning, True

			# call tool with input
			reasoning_step = cast(ActionReasoningStep, current_reasoning[-1])
			if reasoning_step.action in tools_dict:
				tool = tools_dict[reasoning_step.action]
				with self.callback_manager.event(CBEventType.FUNCTION_CALL,
						payload={EventPayload.FUNCTION_CALL: reasoning_step.action_input,
							EventPayload.TOOL: tool.metadata, }, ) as event:
					try:
						tool_output = tool.call(**reasoning_step.action_input)
						print(">>> tool output: \n", tool_output)
						tool_output_str, tool_log = unpack_tool_output(tool_out_json=tool_output.content)
						tool_output.content = tool_output_str
						if tool_log is not None:
							date, h_m_s = get_time()
							additional_kwargs = {
								CHAT_DATE_NAME: date,
								CHAT_TIME_NAME: h_m_s,
							}
							task.extra_state["new_memory"].put(
								ChatMessage(
									content=tool_log,
									role=MessageRole.TOOL,
									additional_kwargs=additional_kwargs,
								)
							)
							task.extra_state["tool_log"].append(tool_log)

					except Exception as e:
						tool_output = ToolOutput(
							content=f"Error: {e!s}",
							tool_name=tool.metadata.name,
							raw_input={"kwargs": reasoning_step.action_input},
							raw_output=e,
							is_error=True,
						)
						print(f">>> {tool_output.content}")
					event.on_end(payload={EventPayload.FUNCTION_OUTPUT: str(tool_output)})
			else:
				tool_output = self._handle_nonexistent_tool_name(reasoning_step)

		task.extra_state["sources"].append(tool_output)

		observation_step = ObservationReasoningStep(
			observation=str(tool_output),
			return_direct=(tool.metadata.return_direct and not tool_output.is_error if tool else False),
		)
		current_reasoning.append(observation_step)
		if self._verbose:
			print_text(f"{observation_step.get_content()}\n", color="blue")
		return (current_reasoning, tool.metadata.return_direct and not tool_output.is_error if tool else False,)

	async def _aprocess_actions(
		self,
		task: Task,
		tools: Sequence[AsyncBaseTool],
		output: ChatResponse,
		is_streaming: bool = False,
	) -> Tuple[List[BaseReasoningStep], bool]:
		tools_dict = {tool.metadata.name: tool for tool in tools}
		tool = None

		try:
			_, current_reasoning, is_done = self._extract_reasoning_step(output, is_streaming)
		except ValueError as exp:
			current_reasoning = []
			tool_output = self._handle_reasoning_failure_fn(self.callback_manager, exp)
		else:
			if is_done:
				return current_reasoning, True

			# call tool with input
			reasoning_step = cast(ActionReasoningStep, current_reasoning[-1])
			if reasoning_step.action in tools_dict:
				tool = tools_dict[reasoning_step.action]
				with self.callback_manager.event(CBEventType.FUNCTION_CALL,
						payload={EventPayload.FUNCTION_CALL: reasoning_step.action_input,
							EventPayload.TOOL: tool.metadata, }, ) as event:
					try:
						tool_output = await tool.acall(**reasoning_step.action_input)
						tool_output_str, tool_log = unpack_tool_output(tool_out_json=tool_output.content)
						tool_output.content = tool_output_str
						if tool_log is not None:
							date, h_m_s = get_time()
							additional_kwargs = {
								CHAT_DATE_NAME: date,
								CHAT_TIME_NAME: h_m_s,
							}
							task.extra_state["new_memory"].put(
								ChatMessage(
									content=tool_log,
									role=MessageRole.TOOL,
									additional_kwargs=additional_kwargs,
								)
							)
					except Exception as e:
						tool_output = ToolOutput(content=f"Error: {e!s}", tool_name=tool.metadata.name,
							raw_input={"kwargs": reasoning_step.action_input}, raw_output=e, is_error=True, )
					event.on_end(payload={EventPayload.FUNCTION_OUTPUT: str(tool_output)})
			else:
				tool_output = self._handle_nonexistent_tool_name(reasoning_step)

		task.extra_state["sources"].append(tool_output)

		observation_step = ObservationReasoningStep(observation=str(tool_output),
			return_direct=(tool.metadata.return_direct and not tool_output.is_error if tool else False), )

		current_reasoning.append(observation_step)
		if self._verbose:
			print_text(f"{observation_step.get_content()}\n", color="blue")
		return (current_reasoning, tool.metadata.return_direct and not tool_output.is_error if tool else False,)

	def finalize_task(self, task: Task, **kwargs: Any) -> None:
		"""Finalize task, after all the steps are completed."""
		user_id = task.extra_state.get("user_id", None)
		chat_group_id = task.extra_state.get("chat_group_id", None)

		if chat_group_id is not None:
			if chat_group_id in self.chat_group_id_list:
				update_chat_memory(
					memory_id=user_id,
					chat_messages=task.extra_state["new_memory"].get_all(),
				)
			else:
				if self._verbose:
					print_text(f"The chat group {chat_group_id} is not registered.", color="cyan", end="\n")
		else:
			if user_id in self.user_id_list:
				update_chat_memory(
					memory_id=user_id,
					chat_messages=task.extra_state["new_memory"].get_all(),
				)
			else:
				if self._verbose and user_id is not None:
					print_text(f"{user_id} is not registered as a user.", color="cyan", end="\n")

		# add new messages to memory
		task.memory.set(task.memory.get_all() + task.extra_state["new_memory"].get_all())
		# reset new memory
		task.extra_state["new_memory"].reset()