import streamlit as st
from streamlit_chat import message
from multiprocessing.connection import Client


@st.cache_data
def get_client():
	c = Client(('127.0.0.1', 8000))
	return c


if __name__ == "__main__":
	client = get_client()
	st.markdown("#### LABRIDGE")
	if 'generated' not in st.session_state:
		st.session_state['generated'] = []
	if 'past' not in st.session_state:
		st.session_state['past'] = []
	user_input = st.text_input("请输入您的问题:", key='input')
	if user_input:
		print("Input: ", user_input)
		client.send(user_input)
		output = client.recv()
		st.session_state['past'].append(user_input)
		st.session_state['generated'].append(output)
	if st.session_state['generated']:
		for i in range(len(st.session_state['generated']) - 1, -1, -1):
			message(st.session_state["generated"][i], key=str(i))
			message(st.session_state['past'][i], is_user=True, key=str(i) + '_user')

	# while True:
	# 	query = input("User: ")
	# 	client.send(query)
	# 	output = client.recv()
	# 	print("Agent: \n", output)
