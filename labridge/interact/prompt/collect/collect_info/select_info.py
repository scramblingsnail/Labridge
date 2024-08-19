from llama_index.core.prompts.base import PromptTemplate, PromptType


COLLECT_SELECT_INFO_TMPL = (
	"You are deciding the relevance of providing paragraphs to the user's statement.\n"
	"The theme of these contents and the theme description is as follows:\n"
	"{required_infos_str}\n\n"
    "A list of paragraphs about this theme is shown below. Each paragraph has a number next to it along "
    "with a detailed description. The user's statement is also provided. \n"
    "Respond with the numbers of the paragraphs "
    "you should consult to answer the question, in order of relevance, as well \n"
    "as the relevance score. The relevance score is a number from 1-10 based on "
    "how relevant you think the paragraph is to the user's statement.\n"
    "Do not include any paragraphs that are not relevant to the statement.\n"
	"you ONLY need to return the NUMBERS of the paragraphs and the RELEVANCE SCORES\n"
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
    "User's statement: {user_response_str}\n"
    "Answer:\n"
)
COLLECT_SELECT_INFO_PROMPT = PromptTemplate(
    COLLECT_SELECT_INFO_TMPL,
	prompt_type=PromptType.CHOICE_SELECT
)
