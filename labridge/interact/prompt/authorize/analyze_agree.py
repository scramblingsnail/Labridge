from llama_index.core.prompts.base import PromptTemplate, PromptType


ANALYZE_AGREE_WORD = "yes"
ANALYZE_DISAGREE_WORD = "no"


AUTHORIZATION_ANALYZE_TMPL = (
	"Someone tried to obtain authorization from the user to perform a specific operation, "
	"following is the user's response, please judge whether the user agrees.\n"
	"If the user agrees, please output <{agree_word}>,\n"
	"If the user does not agree, please output <{disagree_word}>\n"
	"You should not output anything beyond <{agree_word}> and <{disagree_word}>.\n\n"
	"The user's response is as follows:\n"
	"User: {user_response}\n"
	"Whether the user agree:"
)
AUTHORIZATION_ANALYZE_PROMPT = PromptTemplate(
    AUTHORIZATION_ANALYZE_TMPL, prompt_type=PromptType.CHOICE_SELECT
)