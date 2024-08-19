

# 先不考虑文献库扩充的问题，先写如下内容：
# 1. 文献下载
# 2. 文献总结
# 3. 每日文献推荐 pipeline -> 根据研究领域下载文献 -> 分析相关性 -> 总结有价值的文献。

def summarize_paper(paper_path: str):
	r""" 是否需要为所有的未在warehouse中的paper构建一个临时仓库，并按时清理即可。比如构建临时的summary index，避免重复进行总结。
	也避免出现 file_path 出问题，而是检索。 """
	return