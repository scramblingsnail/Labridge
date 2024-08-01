import datetime
import time
import json

from typing import Tuple


CHAT_DATE_FORMAT = "%Y-%m-%d"
CHAT_TIME_FORMAT = "%H:%M:%S"


def get_time() -> Tuple[str, str]:
	now = time.strftime(f"{CHAT_DATE_FORMAT} {CHAT_TIME_FORMAT}")
	date, h_m_s = now.split()
	return date, h_m_s


def str_to_date(date_str: str) -> datetime.date:
	year_month_day = date_str.split("-")

	try:
		my_date = datetime.date(
			year=int(year_month_day[0]),
			month=int(year_month_day[1]),
			day=int(year_month_day[2]),
		)
		return my_date
	except Exception:
		raise ValueError(f"The input date string {date_str} is invalid.")


def str_to_time(time_str: str) -> datetime.time:
	hour_minute_second = time_str.split(":")

	try:
		my_time = datetime.time(
			hour=int(hour_minute_second[0]),
			minute=int(hour_minute_second[1]),
			second=int(hour_minute_second[2]),
		)
		return my_time
	except Exception:
		raise ValueError(f"The input time string {time_str} is invalid.")


def str_to_datetime(date_str: str, time_str: str) -> datetime.datetime:
	my_date = str_to_date(date_str)
	my_time = str_to_time(time_str)
	my_datetime = datetime.datetime(
		year=my_date.year,
		month=my_date.month,
		day=my_date.day,
		hour=my_time.hour,
		minute=my_time.minute,
		second=my_time.second,
	)
	return my_datetime


def pack_user_message(user_id: str, message_str: str, chat_group_id: str = None):
	if chat_group_id is None:
		user_message = (
			f"You are chatting with a user one-to-one\n"
			f"User id: {user_id}\n"
			f"Message: {message_str}\n"
		)
	else:
		user_message = (
			f"You are in a group chat, the chat group id is {chat_group_id}\n"
			f"A user in this group has sent a message to you:\n"
			f"User id: {user_id}\n"
			f"Message: {message_str}\n"
		)
	message_dict = {
		"user_id": user_id,
		"chat_group_id": chat_group_id,
		"message": user_message,
	}
	message_str = json.dumps(message_dict)
	return message_str


def unpack_user_message(message_str: str):
	message_dict = json.loads(message_str)
	user_id, chat_group_id, message = message_dict["user_id"], message_dict["chat_group_id"], message_dict["message"]
	return user_id, chat_group_id, message
