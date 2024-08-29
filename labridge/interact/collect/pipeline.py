from llama_index.core.llms import LLM
from llama_index.core.settings import Settings

from labridge.interact.collect.types.info_base import CollectingInfoBase
from labridge.interact.collect.collector.common_collector import CommonInfoCollector
from labridge.interact.collect.collector.select_collector import SelectInfoCollector

from typing import List, Optional, Dict


def collect_info_from_user(
	user_id: str,
	required_infos: List[CollectingInfoBase],
	query_str: str,
	llm: LLM = None,
) -> Optional[Dict[str, str]]:
	r"""
	This is a pipeline to collect information from the user.

	Args:
		user_id (str): The user id of a Lab member.
		required_infos (List[CollectingInfoBase]): The required information.
		query_str (str): The query string to be sent to the user.
		llm (LLM): The used LLM.

	Returns:
		Optional[Dict[str, str]]:
			The collected information.

			- key: The information name.
			- value: The collected information.

			If the user aborts the collecting, return None.
	"""
	# # TODO: Send query_str to User
	print(f"Assistant: {query_str}")
	llm = llm or Settings.llm

	# for info in required_infos:
	# 	print(info.info_name)

	common_info_collector = CommonInfoCollector(
		llm=llm,
		required_infos=required_infos,
	)
	select_info_collector = SelectInfoCollector(
		llm=llm,
		required_infos=required_infos,
	)

	abort = False
	header_sent = False

	while not abort and not select_info_collector.collected:
		query = query_str if not header_sent else None
		abort = select_info_collector.collect(user_id=user_id, query_str=query)
		header_sent = True
	select_modify = True
	while not abort and select_modify:
		select_modify, abort = select_info_collector.modify(user_id=user_id)

	while not abort and not common_info_collector.collected:
		query = query_str if not header_sent else None
		abort = common_info_collector.collect(user_id=user_id, query_str=query)
		header_sent = True
	common_modify = True
	while not abort and common_modify:
		common_modify, abort = common_info_collector.modify(user_id=user_id)

	if abort:
		return None

	output_dict = {}
	common_info_dict = common_info_collector.collected_infos
	select_info_dict = select_info_collector.collected_infos
	if common_info_dict is not None:
		output_dict.update(common_info_dict)
	if select_info_dict is not None:
		output_dict.update(select_info_dict)
	return output_dict


async def acollect_info_from_user(
	user_id: str,
	required_infos: List[CollectingInfoBase],
	query_str: str,
	llm: LLM = None,
):
	r"""
	This is an asynchronous pipeline to collect information from the user.

	Args:
		user_id (str): The user id of a Lab member.
		required_infos (List[CollectingInfoBase]): The required information.
		query_str (str): The query string to be sent to the user.
		llm (LLM): The used LLM.

	Returns:
		Optional[Dict[str, str]]:
			The collected information.

			- key: The information name.
			- value: The collected information.

			If the user aborts the collecting, return None.
	"""
	# TODO: Send query_str to User
	print(f"Assistant: {query_str}")
	llm = llm or Settings.llm

	common_info_collector = CommonInfoCollector(
		llm=llm,
		required_infos=required_infos,
	)
	select_info_collector = SelectInfoCollector(
		llm=llm,
		required_infos=required_infos,
	)

	abort = False
	header_sent = False

	while not abort and not select_info_collector.collected:
		query = query_str if not header_sent else None
		abort = await select_info_collector.acollect(user_id=user_id, query_str=query)
		header_sent = True
	select_modify = True
	while not abort and select_modify:
		select_modify, abort = await select_info_collector.amodify(user_id=user_id)

	while not abort and not common_info_collector.collected:
		query = query_str if not header_sent else None
		abort = await common_info_collector.acollect(user_id=user_id, query_str=query)
		header_sent = True
	common_modify = True
	while not abort and common_modify:
		common_modify, abort = await common_info_collector.amodify(user_id=user_id)

	if abort:
		return None

	output_dict = {}
	common_info_dict = common_info_collector.collected_infos
	select_info_dict = select_info_collector.collected_infos
	if common_info_dict is not None:
		output_dict.update(common_info_dict)
	if select_info_dict is not None:
		output_dict.update(select_info_dict)
	return output_dict
