from labridge.func_modules.reference.experiment_log import ExperimentLogRefInfo

from typing import List
from pathlib import Path


def ref_experiment_log_str_to_user(log_refs: List[ExperimentLogRefInfo]) -> str:
	r"""
	Instrument ref info to strings for user. will be used in `tools.utils`

	Args:
		log_refs (List[ExperimentLogRefInfo]): The referred experiment logs.

	Returns:
		The formatted reference string.
	"""
	if len(log_refs) < 1:
		return ""

	header = f"**Referred Experiment Logs:**\n"

	content = [header]
	for ref_info in log_refs:
		content_str = ""
		content_str += f"\t**实验名称:** {ref_info.experiment_name}\n"
		content_str += f"\t**记录时间:** {ref_info.date_time}\n"
		content_str += f"\t**记录文本:** {ref_info.log_str}\n"

		if ref_info.attachment_path is not None:
			attachment_name = Path(ref_info.attachment_path).name
			content_str += f"\t**附件:** {attachment_name}\n"
		content.append(content_str)
	ref_str = "\n".join(content)
	return ref_str


def ref_attachments_file_path(ref_infos: List[ExperimentLogRefInfo]) -> List[str]:
	r""" Get all dumped ExperimentLogRefInfo. """
	return [ref_info.dumps() for ref_info in ref_infos if ref_info.attachment_path is not None]
