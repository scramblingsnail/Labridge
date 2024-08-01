

def summarize_paper(paper_path: str):
	r""" 是否需要为所有的未在warehouse中的paper构建一个临时仓库，并按时清理即可。比如构建临时的summary index，避免重复进行总结。
	也避免出现 file_path 出问题，而是检索。 """
	return