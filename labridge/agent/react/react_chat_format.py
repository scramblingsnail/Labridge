from typing import (
	List,
	Optional,
	Sequence,
)

from llama_index.core.base.llms.types import MessageRole
from llama_index.core.base.llms.types import ChatMessage
from llama_index.core.tools.types import BaseTool
from llama_index.core.agent.react.formatter import get_react_tool_descriptions
from llama_index.core.agent.react.types import (
    BaseReasoningStep,
    ObservationReasoningStep,
)

from labridge.agent.react.prompt import LABRIDGE_CHAT_SYSTEM_HEADER


class InstructChatFormatter(object):
    """Instruct chat formatter."""

    system_header: str = LABRIDGE_CHAT_SYSTEM_HEADER  # default
    context: str = ""  # not needed w/ default

    def format(
        self,
        tools: Sequence[BaseTool],
        chat_history: List[ChatMessage],
		prev_response: str,
		suggestion: str,
        current_reasoning: Optional[List[BaseReasoningStep]] = None,
    ) -> List[ChatMessage]:
        """Format chat history into list of ChatMessage."""
        current_reasoning = current_reasoning or []

        format_args = {
            "tool_desc": "\n".join(get_react_tool_descriptions(tools)),
            "tool_names": ", ".join([tool.metadata.get_name() for tool in tools]),
			"prev_response": prev_response,
			"suggestion": suggestion,
        }
        if self.context:
            format_args["context"] = self.context

        fmt_sys_header = self.system_header.format(**format_args)

        # format reasoning history as alternating user and assistant messages
        # where the assistant messages are thoughts and actions and the user
        # messages are observations
        reasoning_history = []
        for reasoning_step in current_reasoning:
            if isinstance(reasoning_step, ObservationReasoningStep):
                message = ChatMessage(
                    role=MessageRole.USER,
                    content=reasoning_step.get_content(),
                )
            else:
                message = ChatMessage(
                    role=MessageRole.ASSISTANT,
                    content=reasoning_step.get_content(),
                )
            reasoning_history.append(message)

        return [
            ChatMessage(role=MessageRole.SYSTEM, content=fmt_sys_header),
            *chat_history,
            *reasoning_history,
        ]