from llama_index.core.prompts.base import PromptTemplate
from llama_index.core.prompts.prompt_type import PromptType


INSTRUMENT_CHOICE_SELECT_PROMPT_TMPL = (
    "A list of scientific instruments is shown below. Each instruments has a number next to it along "
    "with a description of the instrument. A question is also provided. \n"
    "Respond with the numbers of the instruments "
    "you should decide the relevance of these instruments to the question, "
	"specifically, you should give a relevance score to each instrument, "
	"the relevance score is a number from 1-10 based on "
    "how useful you think the instrument may help to solve the queried question.\n"
    "Do not include any documents that are not relevant to the question. \n"
	"you MUST strictly follow the following format, "
    "you ONLY need to return the NUMBERS of the instruments and the RELEVANCE SCORES in the following format."
    "Anything BEYOND the following format is not need, you should not output any reason or description.\n\n"
    "Example format: \n"
    "Instrument 1:\n<description of instrument 1>\n\n"
    "Instrument 2:\n<description of instrument 2>\n\n"
    "...\n\n"
    "Instrument 8:\n<description of instrument 8>\n\n"
    "Question: <question>\n"
    "Answer:\n"
    "Instrument: 6, Relevance: 7\n"
    "Instrument: 3, Relevance: 4\n"
    "Instrument: 7, Relevance: 3\n\n"
    "Please output valid choices and relevance scores, DO NOT output these examples above: "
    "Instrument: 6, Relevance: 7\n"
    "Instrument: 3, Relevance: 4\n"
    "Instrument: 7, Relevance: 3\n\n"
    "Let's try this now, the instruments and question are shown below: \n\n"
    "{context_str}\n"
    "Question: {query_str}\n"
    "Answer:\n"
)
INSTRUMENT_CHOICE_SELECT_PROMPT = PromptTemplate(
    INSTRUMENT_CHOICE_SELECT_PROMPT_TMPL, prompt_type=PromptType.CHOICE_SELECT
)