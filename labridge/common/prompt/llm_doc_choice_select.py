from llama_index.core.prompts.base import PromptTemplate
from llama_index.core.prompts.prompt_type import PromptType


DOC_CHOICE_SELECT_PROMPT_TMPL = (
    "A list of documents is shown below. Each document has a number next to it along "
    "with a summary of the document. A question is also provided. \n"
    "Respond with the numbers of the documents "
    "you should consult to answer the question, in order of relevance, as well \n"
    "as the relevance score. The relevance score is a number from 1-10 based on "
    "how relevant you think the document is to the question.\n"
    "Do not include any documents that are not relevant to the question. \n"
	"DO NOT answer the question in your response, you ONLY need to return the NUMBERS of the documents"
	"and the RELEVANCE SCORES\n"
    "Example format: \n"
    "Document 1:\n<summary of document 1>\n\n"
    "Document 2:\n<summary of document 2>\n\n"
    "...\n\n"
    "Document 10:\n<summary of document 10>\n\n"
    "Question: <question>\n"
    "Answer:\n"
    "Doc: 6, Relevance: 8\n"
    "Doc: 3, Relevance: 4\n"
    "Doc: 7, Relevance: 3\n\n"
    "Please output valid choices and relevance scores, DO NOT output these examples above: \n"
    "Doc: 6, Relevance: 8\n"
    "Doc: 3, Relevance: 4\n"
    "Doc: 7, Relevance: 3\n\n"
    "Let's try this now, the documents and question are shown below: \n\n"
    "{context_str}\n"
    "Question: {query_str}\n"
    "Answer:\n"
)
DOC_CHOICE_SELECT_PROMPT = PromptTemplate(
    DOC_CHOICE_SELECT_PROMPT_TMPL, prompt_type=PromptType.CHOICE_SELECT
)