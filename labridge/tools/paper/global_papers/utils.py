from labridge.reference import PaperInfo
from typing import List


def ref_papers_str_to_user(ref_infos: List[PaperInfo]) -> str:
	r"""
	Transform the relevant PaperInfos into formatted strings
	that will be added as extra info of the assistant's answer.

	Args:
		ref_infos (List[PaperInfo]): The reference paper infos.

	Returns:
		str: The formatted string.
	"""
	references, ref_titles, valid_refs = [], [], []

	for paper_info in ref_infos:
		if paper_info.title not in ref_titles:
			ref_titles.append(paper_info.title)
			valid_refs.append(paper_info)

	ref_str = f"**REFERENCE:**:\n"
	for paper_info in valid_refs:
		paper_str = f"\t**Title:** {paper_info.title}\n"
		paper_str += f"\t这篇文章由{paper_info.possessor}持有，可以与ta多多交流哦。"
		references.append(paper_str)
	ref_str += "\n".join(references)
	return ref_str


def ref_papers_file_path(ref_infos: List[PaperInfo]) -> List[str]:
	r""" Get all file paths of the PaperInfos. """
	return [paper_info.file_path for paper_info in ref_infos]

