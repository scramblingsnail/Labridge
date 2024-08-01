import datetime
import json

from labridge.common.chat.utils import CHAT_DATE_FORMAT, CHAT_TIME_FORMAT
from ..base import FunctionBaseTool


def get_current_date_time() -> str:
	r"""
	This function is used to get the date of today, current time.
	If you are not sure about current date or time, use this tool to help you.

	The returned date is of the following format: "Year-Month-Day".
	The returned time is of the following format: "Hour:Minute:Time".
	"""
	today = datetime.datetime.today()
	current_date = today.date().strftime(CHAT_DATE_FORMAT)
	current_time = today.time().strftime(CHAT_TIME_FORMAT)
	current_weekday = today.weekday() + 1

	datetime_str = (
		f"Today is {current_date}\n"
		f"Today is the No.{current_weekday} day in a week.\n"
		f"Current time is {current_time}\n"
	)
	return datetime_str

def get_date_time_from_now(backward: bool, days: int) -> str:
	r"""
	This function is used to infer the exact date that a statement means. such as '3 days ago', '2 months later'.

	Args:
		backward (bool): the direction, if the statement means the date earlier than now, it is set to `True`.
			Otherwise, it is `False`.
		days (int): the number of days

	Returns:
		the result date.
	"""
	today = datetime.datetime.today()
	if backward:
		result_datetime = today - datetime.timedelta(days=days)
	else:
		result_datetime = today + datetime.timedelta(days=days)

	result_date = result_datetime.date().strftime(CHAT_DATE_FORMAT)
	result_weekday = result_datetime.weekday() + 1
	direction_str = "ago" if backward else "later"
	datetime_str = (
		f"{days} days {direction_str} is {result_date}\n"
		f"the No.{result_weekday} day in a week.\n"
	)
	return datetime_str


class GetCurrentDateTimeTool(FunctionBaseTool):
	def __init__(self):
		super().__init__(fn=get_current_date_time)

	def log(self) -> str:
		return json.dumps(None)


class GetDateTimeFromNowTool(FunctionBaseTool):
	def __init__(self):
		super().__init__(fn=get_date_time_from_now)

	def log(self) -> str:
		return json.dumps(None)