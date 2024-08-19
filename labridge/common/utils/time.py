import datetime
import time

from typing import Tuple, Dict, List


DATE_FORMAT = "%Y-%m-%d"
TIME_FORMAT = "%H:%M:%S"
DELTA_TIME_FORMAT = "%Hh%Mm%Ss"

DELTA_TIME_FLAG_MAPPING = {
	"h": "hours",
	"m": "minutes",
	"s": "seconds",
}



def get_time() -> Tuple[str, str]:
	now = time.strftime(f"{DATE_FORMAT} {TIME_FORMAT}")
	date, h_m_s = now.split()
	return date, h_m_s

def datetime_to_str(date_time: datetime.datetime) -> Tuple[str, str]:
	date_str = date_time.date().strftime(f"{DATE_FORMAT}")
	time_str = date_time.time().strftime(f"{TIME_FORMAT}")
	return date_str, time_str


def parse_delta_time(time_unit: str) -> Dict[str, int]:
	numbers = [char for char in time_unit if char.isnumeric()]
	flag = [char for char in time_unit if char.isalpha()]

	num = int("".join(numbers))
	flag_str = "".join(flag).lower()

	if flag_str in DELTA_TIME_FLAG_MAPPING.keys():
		key = DELTA_TIME_FLAG_MAPPING.get(flag_str)
		return {key: num}
	return {}

def str_to_delta_time(time_str: str) -> datetime.timedelta:
	hour_minute_second = time_str.split(":")

	default = {
		"hours": 0,
		"minutes": 0,
		"seconds": 0,
	}

	for unit in hour_minute_second:
		parsed_dict = parse_delta_time(time_unit=unit)
		default.update(parsed_dict)

	try:
		delta_time = datetime.timedelta(**default)
		return delta_time
	except Exception:
		raise ValueError(f"The input time string {time_str} is invalid.")


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

def parse_date_list(start_date_str: str, end_date_str: str) -> List[str]:
	start_date = str_to_date(start_date_str)
	end_date = str_to_date(end_date_str)
	if end_date < start_date:
		raise ValueError("The end_date can not be earlier than the start_date!")

	date_list = []
	current_date = start_date
	while current_date <= end_date:
		date_list.append(current_date.strftime(DATE_FORMAT))
		current_date = current_date + datetime.timedelta(days=1)
	return date_list
