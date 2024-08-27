import datetime

from labridge.common.utils.time import DATE_FORMAT, TIME_FORMAT
from labridge.tools.base.function_base_tools import FunctionBaseTool, FuncOutputWithLog
from labridge.tools.base.tool_log import ToolLog, TOOL_OP_DESCRIPTION, TOOL_REFERENCES

from typing import Any


def get_current_date_time() -> FuncOutputWithLog:
	r"""
	This function is used to get the date of today, current time.
	If you are not sure about current date or time, use this tool to help you.

	The returned date is of the following format: "Year-Month-Day".
	The returned time is of the following format: "Hour:Minute:Time".
	"""
	today = datetime.datetime.today()
	current_date = today.date().strftime(DATE_FORMAT)
	current_time = today.time().strftime(TIME_FORMAT)
	current_weekday = today.weekday() + 1

	datetime_str = (
		f"Today is {current_date}\n"
		f"Today is the No.{current_weekday} day in a week.\n"
		f"Current time is {current_time}\n"
	)
	return FuncOutputWithLog(
		fn_output=datetime_str,
		fn_log="",
	)

def get_date_time_from_now(backward: bool, days: int) -> FuncOutputWithLog:
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

	result_date = result_datetime.date().strftime(DATE_FORMAT)
	result_weekday = result_datetime.weekday() + 1
	direction_str = "ago" if backward else "later"
	datetime_str = (
		f"{days} days {direction_str} is {result_date}\n"
		f"the No.{result_weekday} day in a week.\n"
	)
	return FuncOutputWithLog(
		fn_output=datetime_str,
		fn_log="",
	)


class GetCurrentDateTimeTool(FunctionBaseTool):
	def __init__(self):
		super().__init__(fn=get_current_date_time)

	def log(self, **kwargs: Any) -> ToolLog:
		log_to_user = None
		log_to_system = {
			TOOL_OP_DESCRIPTION: f"Use the {self.metadata.name} to get current date and time.",
			TOOL_REFERENCES: None,
		}
		return ToolLog(
			tool_name=self.metadata.name,
			log_to_user=log_to_user,
			log_to_system=log_to_system,
		)


class GetDateTimeFromNowTool(FunctionBaseTool):
	def __init__(self):
		super().__init__(fn=get_date_time_from_now)

	def log(self, **kwargs: Any) -> ToolLog:
		return ToolLog(
			tool_name=self.metadata.name,
			log_to_user=None,
			log_to_system={
				TOOL_OP_DESCRIPTION: "",
				TOOL_REFERENCES: None,
			}
		)