from llama_index.core.prompts.base import PromptTemplate, PromptType


MODIFY_SELECT_INFO_TMPL = (
	"You are going to reselect from several paragraphs according to the user's instruction.\n"
	"The theme of these paragraphs and the theme description is as follows:\n"
	"{required_infos_str}\n\n"
    "A list of paragraphs about this theme is shown below. Each paragraph has a number next to it along "
    "with a detailed description. The user's instruction is also provided. \n"
    "Respond with the numbers of the paragraphs "
    "you should consult to answer the question, in order of possibility, as well \n"
    "as the possibility score. The possibility score is a number from 1-10 based on "
    "how possible you think the user wants you to select the paragraph.\n"
    "Do not include any paragraphs that are not possible to the instruction.\n\n"
	"The previous chose paragraph is as follows\n"
	"{collected_infos_str}\n\n"
	"you ONLY need to return the NUMBERS of the paragraphs and the POSSIBILITY SCORES\n"
    "Example format: \n"
    "Paragraph 1:\n<description of paragraph 1>\n\n"
    "Paragraph 2:\n<description of paragraph 2>\n\n"
    "...\n\n"
    "Paragraph 10:\n<description of paragraph 10>\n\n"
    "User's statement: <statement>\n"
    "Your Answer:\n"
    "Paragraph: 9, Relevance: 7\n"
    "Paragraph: 3, Relevance: 4\n"
    "Paragraph: 7, Relevance: 3\n\n"
    "Please output valid choices and relevance scores, DO NOT output these examples above: \n"
    "Paragraph: 9, Relevance: 7\n"
    "Paragraph: 3, Relevance: 4\n"
    "Paragraph: 7, Relevance: 3\n\n"
    "Let's try this now, the paragraphs and user's statement are shown below: \n\n"
    "{extra_info}\n"
    "User's statement: {user_comment_str}\n"
    "Answer:\n"
)
MODIFY_SELECT_INFO_PROMPT = PromptTemplate(
    MODIFY_SELECT_INFO_TMPL,
	prompt_type=PromptType.CHOICE_SELECT
)
