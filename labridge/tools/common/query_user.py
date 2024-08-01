from ..base import FunctionBaseTool


def query_user(user_id: str, query_str: str) -> str:
	r"""
	This function is used for the assistant to query the user to supplement information
	in a multi-turn Question-Answer process.

	If the assistant think that there is a need to get more information from the user, this function can be used.
	For an example scenario, if some parts of the user's question are too ambiguous to understand, the assistant can request the user
	to specify these ambiguous parts for the assistant's better work.
	Another example scenario, if the assistant is not sure about its reasoning, it can verify its reasoning whether
	matches the user's requirements through this function.
	In summary, when the assistant needs the help of the users, this function can be used.

	Args:
		user_id (str): the user that you want to interact with.
		query_str (str): the question

	Returns:
		user_response (str): the response of the user.
	"""
	# TODO: interface
	print(f">>> Assistant: Dear {user_id}, {query_str}")
	user_response = input("User: ")
	return user_response


class QueryUserTool(FunctionBaseTool):
	def __init__(self):
		super().__init__(fn=query_user)

	def log(self):
		return None
