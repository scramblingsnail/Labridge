import asyncio
import llama_index.core.instrumentation as instrument
from labridge.agent.chat_agent import ChatAgent
from labridge.agent.chat_msg.msg_types import ChatBuffer


dispatcher = instrument.get_dispatcher(__name__)

def chat_one_to_one():
	user_id = "杨再正"

	while True:
		packed_msgs = ChatBuffer.test_get_user_text(user_id=user_id)
		ChatAgent.set_chatting(user_id=user_id, chatting=True)
		if packed_msgs:
			ChatAgent.set_chatting(user_id=user_id, chatting=True)
			agent_response = ChatAgent.test_chat(packed_msgs=packed_msgs)
			print(agent_response.response)

			# ChatBuffer.put_agent_reply(user_id=user_id, reply_str=agent_response.response, references=agent_response.references,
			# 	reply_in_speech=agent_response.reply_in_speech, inner_chat=False, )
			# ChatAgent.set_chatting(user_id=user_id, chatting=False)

async def achat_one_to_one():
	user_id = "杨再正"

	while True:
		packed_msgs = ChatBuffer.test_get_user_text(user_id=user_id)
		ChatAgent.set_chatting(user_id=user_id, chatting=True)
		if packed_msgs:
			ChatAgent.set_chatting(user_id=user_id, chatting=True)
			agent_response = await ChatAgent.chat(packed_msgs=packed_msgs)
			print(agent_response.response)


if __name__ == "__main__":
	chat_one_to_one()

	# asyncio.run(achat_one_to_one())
	# test_async()
