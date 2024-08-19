from labridge.reference.instrument import InstrumentInfo

from typing import List


def ref_instruments_str_to_user(instruments: List[InstrumentInfo]):
	r"""
	 Instrument ref info to strings for user. will be used in `tools.utils`
	 """
	super_users = ",".join(instruments[instrument_id])
	log_string = (f"**Relevant instrument:\n**"
				  f"\t{instrument_id}\n"
				  f"\tSuper users: {super_users}\n\n")
	logs.append(log_string)