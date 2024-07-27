from llama_index.core.prompts.base import PromptTemplate
from llama_index.core.prompts.prompt_type import PromptType


# for summarize a paper directory
DIR_SUMMARIZE_QUERY = (
	"Here are a set of keywords of papers in a directory, "
	"You need to extract the common research fields that all of these papers involve from these keywords."
)

PAPER_KEYWORDS_EXTRACT_QUERY = (
	"Here is a summary of a research paper."
	"You must extract several keywords of the paper. "
	"Output the keywords in a comma-separated format."
)

DIR_CHOICE_SELECT_PROMPT_TMPL = (
    "A list of documents is shown below. Each document has a number next to it along "
    "with several paper keywords representing research fields. Some texts in a research paper is also provided. \n"
    "Respond with the numbers of the documents "
    "whose research fields are relevant to the research paper, in order of relevance, as well \n"
    "as the relevance score. The relevance score is a number from 1-10 based on "
    "how relevant you think the research fields in the document are to the research paper.\n"
    "Do not include any documents that are not relevant to the research paper. \n"
	"you ONLY need to return the NUMBERS of the documents"
	"and the RELEVANCE SCORES\n"
    "Example format: \n"
    "Document 1:\n<research fields in document 1>\n\n"
    "Document 2:\n<research fields in document 2>\n\n"
    "...\n\n"
    "Document 10:\n<research fields in document 10>\n\n"
    "Research paper: <summary of the paper>\n"
    "Answer:\n"
    "Doc: 9, Relevance: 7\n"
    "Doc: 3, Relevance: 4\n"
    "Doc: 7, Relevance: 3\n\n"
    "Please output valid choices and relevance scores, DO NOT output these examples above: \n"
    "Doc: 9, Relevance: 7\n"
    "Doc: 3, Relevance: 4\n"
    "Doc: 7, Relevance: 3\n\n"
    "Let's try this now, the documents and research paper are shown below: \n\n"
    "{dir_context_str}\n"
    "Research paper: {paper_str}\n"
    "Answer:\n"
)
DIR_CHOICE_SELECT_PROMPT = PromptTemplate(
    DIR_CHOICE_SELECT_PROMPT_TMPL, prompt_type=PromptType.CHOICE_SELECT
)

CATEGORY_CHOICE_SELECT_PROMPT_TMPL = (
	"A list of documents is shown below. Each document has a number next to it along "
    "with a research field. The summary of a research paper is also provided. \n"
    "Respond with the numbers of the documents "
    "whose research field is relevant to the research paper, in order of relevance, as well \n"
    "as the relevance score. The relevance score is a number from 1-100 based on "
    "how relevant you think the research field in the document is to the research paper.\n"
    "Do not include any documents that are not relevant to the research paper. \n"
	"you ONLY need to return the NUMBERS of the documents"
	"and the RELEVANCE SCORES\n"
    "Example format: \n"
    "Document 1:\n<research field in document 1>\n\n"
    "Document 2:\n<research field in document 2>\n\n"
    "...\n\n"
    "Document 10:\n<research field in document 10>\n\n"
    "Research paper: <summary of the paper>\n"
    "Answer:\n"
    "Doc: 9, Relevance: 28\n"
    "Doc: 3, Relevance: 43\n"
    "Doc: 7, Relevance: 88\n\n"
    "Please output valid choices and relevance scores, DO NOT output these examples above: \n"
    "Doc: 9, Relevance: 28\n"
    "Doc: 3, Relevance: 43\n"
    "Doc: 7, Relevance: 88\n\n"
    "Let's try this now, the documents and research paper are shown below: \n\n"
    "{category_context_str}\n"
    "Research paper: {paper_str}\n"
    "Answer:\n"
)
CATEGORY_CHOICE_SELECT_PROMPT = PromptTemplate(
    CATEGORY_CHOICE_SELECT_PROMPT_TMPL, prompt_type=PromptType.CHOICE_SELECT
)