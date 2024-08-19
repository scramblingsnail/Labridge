import multiprocessing
import time

from llama_index.core.agent.react.formatter import ReActChatFormatter
from llama_index.core.tools.query_engine import QueryEngineTool
from llama_index.core.agent.react.base import ReActAgent

from labridge.common.chat.chat import MY_REACT_CHAT_SYSTEM_HEADER, ZH_CHAT_MOTIVATION_TMPL
from labridge.paper.query_engine.utils import get_default_paper_query_engines
from labridge.common.query_engine.query_engines import SingleQueryEngine
from labridge.llm.models import get_models, get_reranker
from labridge.paper.query_engine.paper_query_engine import (
	PAPER_QUERY_TOOL_NAME,
	PAPER_QUERY_TOOL_DESCRIPTION,
	PAPER_SUB_QUERY_TOOL_NAME,
	PAPER_SUB_QUERY_TOOL_DESCRIPTION,
)


def get_chat_engine():
	llm, embed_model = get_models()
	re_ranker = get_reranker()
	paper_query_engine, paper_sub_query_engine = get_default_paper_query_engines(
		llm=llm,
		embed_model=embed_model,
		re_ranker=re_ranker,
	)
	motivation_engine = SingleQueryEngine(llm=llm, prompt_tmpl=ZH_CHAT_MOTIVATION_TMPL)
	motivation_tool = QueryEngineTool.from_defaults(
		query_engine=motivation_engine,
		name="motivation_analyzer",
		description="This tool is used to analyze the motivation of the user's query.",
	)

	paper_query_tool = QueryEngineTool.from_defaults(
		query_engine=paper_query_engine,
		name=PAPER_QUERY_TOOL_NAME,
		description=PAPER_QUERY_TOOL_DESCRIPTION,
	)
	paper_sub_query_tool = QueryEngineTool.from_defaults(
		query_engine=paper_sub_query_engine,
		name=PAPER_SUB_QUERY_TOOL_NAME,
		description=PAPER_SUB_QUERY_TOOL_DESCRIPTION,
	)

	# react chat formatter
	react_chat_formatter = ReActChatFormatter.from_defaults(system_header=MY_REACT_CHAT_SYSTEM_HEADER)
	chat_engine = ReActAgent.from_tools(
		tools=[
			motivation_tool,
			# paper_query_tool,
			paper_sub_query_tool
		],
		react_chat_formatter=react_chat_formatter,
		verbose=True,
		llm=llm)
	return chat_engine

def do_socket(conn, addr, chat_engine):
	try:
		while True:
			if conn.poll(1) == False:
				time.sleep(0.5)
				continue
			query = conn.recv()
			print("User: ", query)
			response = chat_engine.chat(message=query)
			chat_engine.memory.set([])
			conn.send(response.response)
			print("Agent:", response)

	except Exception as e:
		print('Socket Error', e)

	finally:
		try:
			conn.close()
			print('Connection close.', addr)
		except:
			print('close except')


def run_server(host, port):
	from multiprocessing.connection import Listener
	server_sock = Listener((host, port))

	print("Sever running...", host, port)

	# pool = multiprocessing.Pool(10)
	while True:
		# 接受一个新连接:
		conn = server_sock.accept()
		addr = server_sock.last_accepted
		print('Accept new connection', addr)

		# 创建进程来处理TCP连接:
		do_socket(conn, addr, my_chat_engine)
		# pool.apply_async(func=do_socket, args=(conn, addr, my_chat_engine))


if __name__ == '__main__':
	multiprocessing.set_start_method('spawn')
	server_host = '127.0.0.1'
	server_port = 8000
	my_chat_engine = get_chat_engine()
	run_server(server_host, server_port)
