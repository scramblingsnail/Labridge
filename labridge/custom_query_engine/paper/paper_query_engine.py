from typing import Optional

from llama_index.core.response_synthesizers.tree_summarize import TreeSummarize
from llama_index.core.postprocessor.sbert_rerank import BaseNodePostprocessor
from llama_index.core.question_gen.llm_generators import LLMQuestionGenerator
from llama_index.core.question_gen.types import BaseQuestionGenerator
from llama_index.core.response_synthesizers import BaseSynthesizer
from llama_index.core.tools.query_engine import QueryEngineTool
from llama_index.core.selectors import LLMMultiSelector
from llama_index.core.llms import LLM
from llama_index.core.query_engine import (
    RetrieverQueryEngine,
    RouterQueryEngine,
    SubQuestionQueryEngine,
)

from ...prompt.synthesize import PAPER_TREE_SUMMARIZE_PROMPT_SEL
from ...retrieve.paper.paper_retriever import (
    PaperSummaryRetriever,
    PaperDetailRetriever,
)


PAPER_DERAIL_QUERY_TOOL_NAME = "Paper_detail_query_tool"
PAPER_DERAIL_QUERY_TOOL_DESCRIPTION = (
    "This Query engine tool is useful to answer detailed questions of research papers."
)

PAPER_SUMMARY_QUERY_TOOL_NAME = "Paper_summary_query_tool"
PAPER_SUMMARY_QUERY_TOOL_DESCRIPTION = (
    "This Query engine tool helps you to to answer questions with the previously summarized summaries of research papers."
    "The summaries are about:\n"
    "1. A brief summary to each research paper's work."
    "2. The main innovations of each research paper."
    "3. The relevant fields of each paper."
    "4. Which fields may be interested in this paper."
    "\n"
    "If the query is about these aspects, you can use this tool to use the pre-summarized texts."
)

PAPER_QUERY_TOOL_NAME = "Paper_query_tool"
PAPER_QUERY_TOOL_DESCRIPTION = (
	"This tool helps you to answer the query with the access to abundant research papers."
	"When answering academic queries, use this tool to make your answer accurate, professional, and convincing."
)

PAPER_SUB_QUERY_TOOL_NAME = "Paper_sub_queries_tool"
PAPER_SUB_QUERY_TOOL_DESCRIPTION = (
	"This tool help you to answer the query with the access to abundant research papers.\n"
	"IN ADDITION, This tool helps you to decompose the complex query into several sub-queries, "
	"then utilize the information in these research papers to answer these sub-queries,"
	"finally merge these information to obtain the answer of the complex raw query.\n"
	"When answering COMPLEX academic queries, use this tool to make your answer logical, comprehensive and professional."
)

class PaperSummaryQueryEngine(RetrieverQueryEngine):
    r"""
    TODO: Docstring
    """
    def __init__(self,
                 llm: LLM,
                 paper_summary_retriever: PaperSummaryRetriever,
                 re_ranker: BaseNodePostprocessor,
                 verbose: bool = False):
        response_synthesizer = TreeSummarize(
            llm=llm,
            callback_manager=paper_summary_retriever.callback_manager,
            summary_template=PAPER_TREE_SUMMARIZE_PROMPT_SEL,
            verbose=verbose,)
        super().__init__(retriever=paper_summary_retriever,
                         node_postprocessors=[re_ranker, ],
                         response_synthesizer=response_synthesizer)

class PaperDetailQueryEngine(RetrieverQueryEngine):
    r"""
    TODO: Docstring
    """
    def __init__(self,
                 llm: LLM,
                 paper_detail_retriever: PaperDetailRetriever,
                 re_ranker: BaseNodePostprocessor,
                 verbose: bool = False):
        response_synthesizer = TreeSummarize(
            llm=llm,
            callback_manager=paper_detail_retriever.callback_manager,
            summary_template=PAPER_TREE_SUMMARIZE_PROMPT_SEL,
            verbose=verbose,)
        super().__init__(retriever=paper_detail_retriever,
                         node_postprocessors=[re_ranker, ],
                         response_synthesizer=response_synthesizer)


class PaperQueryEngine(RouterQueryEngine):
    r"""
    TODO: Docstring
    """
    def __init__(self,
                 llm: LLM,
                 paper_detail_query_engine: PaperDetailQueryEngine,
                 paper_summary_query_engine: PaperSummaryQueryEngine,
                 verbose: bool = False):
        detail_query_tool = QueryEngineTool.from_defaults(
            query_engine=paper_detail_query_engine,
            name=PAPER_DERAIL_QUERY_TOOL_NAME,
            description=PAPER_DERAIL_QUERY_TOOL_DESCRIPTION)

        summary_query_tool = QueryEngineTool.from_defaults(
            query_engine=paper_summary_query_engine,
            name=PAPER_SUMMARY_QUERY_TOOL_NAME,
            description=PAPER_SUMMARY_QUERY_TOOL_DESCRIPTION)

        super().__init__(
            selector=LLMMultiSelector.from_defaults(llm=llm),
            query_engine_tools=[detail_query_tool, summary_query_tool],
            llm=llm,
            verbose=verbose,
        )


class PaperSubQueryEngine(SubQuestionQueryEngine):
    def __init__(self,
				 llm: LLM,
				 paper_query_engine: PaperQueryEngine,
				 question_gen: Optional[BaseQuestionGenerator] = None,
				 response_synthesizer: Optional[BaseSynthesizer] = None,
				 verbose: bool = True,
				 use_async: bool = True, ):
        paper_query_tool = QueryEngineTool.from_defaults(
            query_engine=paper_query_engine,
            name=PAPER_QUERY_TOOL_NAME,
            description=PAPER_QUERY_TOOL_DESCRIPTION)
        callback_manager = paper_query_engine.callback_manager
        if question_gen is None:
            try:
                from llama_index.question_gen.openai import (OpenAIQuestionGenerator, )  # pants: no-infer-dep

                # try to use OpenAI function calling based question generator.
                # if incompatible, use general LLM question generator
                question_gen = OpenAIQuestionGenerator.from_defaults(llm=llm)

            except ImportError as e:
                raise ImportError("`llama-index-question-gen-openai` package cannot be found. "
                                  "Please install it by using `pip install `llama-index-question-gen-openai`")
            except ValueError:
                question_gen = LLMQuestionGenerator.from_defaults(llm=llm)

            response_synthesizer = TreeSummarize(
                llm=llm,
                callback_manager=callback_manager,
                summary_template=PAPER_TREE_SUMMARIZE_PROMPT_SEL,
                verbose=verbose,
                use_async=use_async
            )

        super().__init__(
            question_gen=question_gen,
            response_synthesizer=response_synthesizer,
            query_engine_tools=[paper_query_tool],
            callback_manager=callback_manager,
            verbose=verbose,
            use_async=use_async,
        )
