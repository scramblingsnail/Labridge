import json
from labridge.common.utils.time import get_time


# def pack_user_message(user_id: str, user_msg: str, system_msg: str, chat_group_id: str = None):
# 	r""" TODO: change to system format """
# 	date_str, time_str = get_time()
# 	if chat_group_id is None:
# 		user_message = (
# 			f"You are chatting with a user one-to-one\n"
# 			f"User id: {user_id}\n"
# 			f"Message: {message_str}\n"
# 			f"Current date: {date_str}\n"
# 			f"Current time: {time_str}\n"
# 		)
# 	else:
# 		user_message = (
# 			f"You are in a group chat, the chat group id is {chat_group_id}\n"
# 			f"A user in this group has sent a message to you:\n"
# 			f"User id: {user_id}\n"
# 			f"Message: {message_str}\n"
# 			f"Current date: {date_str}\n"
# 			f"Current time: {time_str}\n"
# 		)
# 	message_dict = {
# 		"user_id": user_id,
# 		"chat_group_id": chat_group_id,
# 		"message": user_message,
# 	}
# 	message_str = json.dumps(message_dict)
# 	return message_str


# def unpack_user_message(message_str: str):
# 	message_dict = json.loads(message_str)
# 	user_id, chat_group_id, message = message_dict["user_id"], message_dict["chat_group_id"], message_dict["message"]
# 	return user_id, chat_group_id, message


def pack_user_message(user_id: str, user_msg: str, system_msg: str, reply_in_speech: bool):
	r""" TODO: change to system format """
	message_dict = {
		"user_id": user_id,
		"user_message": user_msg,
		"system_message": system_msg,
	}
	message_str = json.dumps(message_dict)
	return message_str


# def unpack_user_message(message_str: str):
# 	message_dict = json.loads(message_str)
# 	user_id, user_message, system_message = message_dict["user_id"], message_dict["user_message"], message_dict["system_message"]
# 	return user_id, user_message, system_message


