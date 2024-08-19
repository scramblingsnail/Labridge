from llama_index.core.prompts.base import PromptTemplate, PromptType


COLLECT_ABORT_WORD = "yes"
COLLECT_CONTINUE_WORD = "no"

COLLECT_ABORT_TMPL = (
"""
You are collecting some information from the user, it perhaps takes several chats.
The user has given a response, 
now you should analyze whether the user want to abort this information collecting process.
If the user want to abort, please output <{abort_word}>.
If the user answers actively and tends to continue, please output <{continue_word}>.

The user's response is as follows:
User: {user_response}
Whether user tends to abort:
"""
)

COLLECT_ABORT_PROMPT = PromptTemplate(
	COLLECT_ABORT_TMPL, prompt_type=PromptType.SINGLE_SELECT
)

COLLECT_ABORT_MSG = (
"""
好的，如果有其它需要我随时可以帮助您。
"""
)