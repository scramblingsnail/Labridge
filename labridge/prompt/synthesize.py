from llama_index.core.prompts import SelectorPromptTemplate
from llama_index.core.prompts.base import PromptTemplate, PromptType
from llama_index.core.prompts.default_prompt_selectors import default_tree_summarize_conditionals


PAPER_TREE_SUMMARIZE_TMPL = (
    "Context information from multiple chunks of several research papers is below.\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Given the information from multiple sources and not prior knowledge, "
    "You also need to attach the meta data of the paper that you refer to in your answer.\n"
    "Including: \n"
    "**Title**, **Possessor**\n"
    "search for these information in the metadata of the text chunk you refer to, do not repeat.\n"
    "If the **Title** is not found, you can use **ref_doc_id** instead.\n"
    "For example:\n\n"
    "References start\n"
    "**Reference paper 1**\n"
    "\t**Title**: <the meta data 'Title'>\n"
    "\t**Possessor**: <the meta data 'Possessor'\n>"
    "**Reference paper 2**\n"
    "\t**Title**: <the meta data 'Title'>\n"
    "\t**Possessor:** <the meta data 'Possessor'\n>"
    "References end\n\n"
    "Finally give your answer to the query.\n"
    "Query: {query_str}\n"
    "Answer: <your answer>"
)


PAER_TREE_SUMMARIZE_PROMPT = PromptTemplate(
    PAPER_TREE_SUMMARIZE_TMPL, prompt_type=PromptType.SUMMARY
)

PAPER_TREE_SUMMARIZE_PROMPT_SEL = SelectorPromptTemplate(
    default_template=PAER_TREE_SUMMARIZE_PROMPT,
    conditionals=default_tree_summarize_conditionals,
)

PAPER_SUB_QUERY_TREE_SUMMARIZE_TMPL = (
    "Context information from multiple chunks of several research papers is below.\n"
    "---------------------\n"
    "{context_str}\n"
    "---------------------\n"
    "Given the information from multiple sources and not prior knowledge, "
    "You also need to attach the meta data of the paper that you refer to in your answer.\n"
    "Including: \n"
    "**Title**, **Possessor**\n"
    "search for these information in the metadata of the text chunk you refer to, do not repeat.\n"
    "If the **Title** is not found, you can use **ref_doc_id** instead.\n"
    "For example:\n\n"
    "References start\n"
    "**Reference paper 1**\n"
    "\t**Title**: <the meta data 'Title'>\n"
    "\t**Possessor**: <the meta data 'Possessor'\n>"
    "**Reference paper 2**\n"
    "\t**Title**: <the meta data 'Title'>\n"
    "\t**Possessor:** <the meta data 'Possessor'\n>"
    "References end\n\n"
    "Finally give your answer to the query.\n"
    "Query: {query_str}\n"
    "Answer: <your answer>"
)
