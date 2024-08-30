from labridge.func_modules.reference.instrument import InstrumentInfo

from typing import List


def ref_instruments_str_to_user(instruments: List[InstrumentInfo]) -> str:
	r"""
	 Instrument ref info to strings for user. will be used in `tools.utils`
	 """

	ref_str = f"**INSTRUMENT:**\n"
	for instrument_info in instruments:
		ref_str += f"\t**仪器工具名称:** {instrument_info.instrument_id}\n"
		super_users = ",".join(instrument_info.super_users)
		ref_str += f"\t**Super-users:** {super_users}\n"
	ref_str += "有什么问题可以向这些经验丰富的Super-users请教哦。"
	return ref_str
