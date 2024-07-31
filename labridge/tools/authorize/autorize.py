import time
from func_timeout import FunctionTimedOut, func_timeout


def authorize_request(user_id: str, action_desc: str, timeout: int = 5) -> bool:
	# TODO: Interface: output
	print(f">>> Dear {user_id}: "
		  f"I'm asking your permission to do the following actions, please reply with 'yes' or 'no':\n{action_desc}")
	try:
		# TODO: Interface: input
		input_str = func_timeout(timeout, lambda: input("Answer: "))
		print(input_str)
	except FunctionTimedOut:
		print("Time out")
		input_str = "no"

	if input_str == "yes":
		return True
	else:
		return False


def query_user(user_id: str, query: str, timeout: int = 10) -> str:
	# TODO: Interface: output
	print(f">>> Dear {user_id}: {query}")

	try:
		# TODO: Interface: input
		input_str = func_timeout(timeout, lambda: input("Answer: "))
	except FunctionTimedOut:
		print("Time out")
		input_str = f"The user {user_id} do not reply."
	return input_str



authorize_request("zhisan", "Move the new paper to the folder: ccc")
