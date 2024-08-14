import llama_index.core.instrumentation as instrument

from llama_index.core.agent.react.formatter import ReActChatFormatter
from llama_index.core.memory.chat_memory_buffer import ChatMemoryBuffer

from labridge.common.chat.chat import MY_REACT_CHAT_SYSTEM_HEADER, ZH_CHAT_MOTIVATION_TMPL
from labridge.paper.query_engine.utils import get_default_paper_query_engines
from labridge.common.query_engine.query_engines import SingleQueryEngine
from labridge.llm.models import get_models, get_reranker

from llama_index.core import Settings
from labridge.common.chat.react import InstructReActAgent
from labridge.tools.paper.simple import AddNumberTool, MultiplyNumberTool
from labridge.tools.common.query_user import QueryUserTool
from labridge.tools.paper.paper_warehouse import PaperQueryTool
from labridge.common.chat.utils import pack_user_message
from labridge.accounts.users import AccountManager
from labridge.tools.memory.retrieve import ChatMemoryRetrieverTool
from labridge.tools.common.date_time import GetCurrentDateTimeTool, GetDateTimeFromNowTool


dispatcher = instrument.get_dispatcher(__name__)


def get_chat_engine():
	llm, embed_model = get_models()
	Settings.embed_model = embed_model
	Settings.llm = llm
	# re_ranker = get_reranker()
	paper_query_engine, paper_sub_query_engine, paper_retriever = get_default_paper_query_engines(
		llm=llm,
		embed_model=embed_model,
		# re_ranker=re_ranker,
	)
	motivation_engine = SingleQueryEngine(llm=llm, prompt_tmpl=ZH_CHAT_MOTIVATION_TMPL)

	chat_history_retrieve_tool = ChatMemoryRetrieverTool()

	paper_query_tool = PaperQueryTool(paper_query_engine=paper_query_engine)
	add_tool = AddNumberTool()
	mul_tool = MultiplyNumberTool()
	query_user_tool = QueryUserTool()
	current_datetime_tool = GetCurrentDateTimeTool()
	datetime_from_now_tool = GetDateTimeFromNowTool()

	# react chat formatter

	tools = [
		add_tool,
		mul_tool,
		paper_query_tool,
		chat_history_retrieve_tool,
		# query_user_tool,
		# current_datetime_tool,
		# datetime_from_now_tool,
	]

	react_chat_formatter = ReActChatFormatter.from_defaults(system_header=MY_REACT_CHAT_SYSTEM_HEADER)

	chat_engine = InstructReActAgent.from_tools(
		tools=tools,
		react_chat_formatter=react_chat_formatter,
		verbose=False,
		llm=llm,
		memory=ChatMemoryBuffer.from_defaults(token_limit=3000),
		enable_instruct=False,
		enable_comment=False,
	)
	return chat_engine

def chat_one_to_one():
	chat_engine = get_chat_engine()
	user_id = "杨再正"

	account_manager = AccountManager()
	account_manager.add_user(user_id=user_id, password="123456")
	while True:
		user_query = input("User: ")
		# query format:
		message = pack_user_message(
			user_id=user_id,
			chat_group_id=None,
			message_str=user_query,
		)
		# print(message)
		response = chat_engine.chat(message=message)
		print("Response: ", response)


def chat_in_group():
	chat_engine = get_chat_engine()
	user_id = "杨再正"
	chat_group_id = "啊对对对队"

	account_manager = AccountManager()
	account_manager.add_user(user_id, password="123456")
	account_manager.add_chat_group(chat_group_id=chat_group_id, user_list=[user_id,])

	while True:
		user_query = input("User: ")

		print(chat_engine.memory.chat_store.store.keys())

		# query format:
		message = pack_user_message(
			user_id=user_id,
			chat_group_id=chat_group_id,
			message_str=user_query,
		)
		print(message)
		response = chat_engine.chat(message=message)
		print("Response: ", response)


def show_file(file_path):
	pass

if __name__ == "__main__":
	chat_one_to_one()


