r"""
This file including the temporary paper info store that including the recent paper of each user.
Each index is attributed to a user.
"""


class RecentPaperStore(object):
	r"""
	paper info index: record the paper info. --> search --> add info into index

	summary_index: summary of each index. --> summarize request --> retrieve --> if ref_doc_id do not exist --> summarize into index

	vector_index: the paper chunks. --> search full paper request --> 

	"""
