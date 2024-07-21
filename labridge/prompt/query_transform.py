############################################
# Rewrite
##############################################
REWRITE_QUERY_TMPL = (
	"The user's query might be ambiguous or not accurate enough. "
	"You need to rewrite this query to make it clearly expressing the user's demands.\n\n"
	"For example: \n"
	"**User query**: <>"
)

############################################
# HYDE
##############################################
ZH_HYDE_TMPL = (
	"请写一段文字来回答如下问题。\n"
	"请尽可能多地在这段话中包括关键信息。\n"
	"\n"
	"\n"
	"{context_str}\n"
	"\n"
	"\n"
	"返回的文字：\n"
)

############################################
# Knowledge-Graph Table
# 此prompt中的`text`指的是 `SimpleLLMPathExtractor`的 `_aextract` 方法中给入的 `text`参数
##############################################
ZH_KG_TRIPLET_EXTRACT_TMPL = (
    "下面给出了一些文本。请从这些文本中提取出最多{max_knowledge_triplets}个知识图谱三元组，这些三元组的形式为：(实体一， 关系， 实体二)。"
	"要避免出现停用词。\n"
	"---------------------\n"
	"举例：\n"
	"文本内容：小红是张三的妈妈。\n"
	"三元组：\n(小红, 是某人的妈妈, 张三)\n"
	"文本内容：朝花夕食是一家2002年创建于南京大学的超市。\n"
	"三元组：\n"
	"(朝花夕食, 是, 超市)\n"
	"(朝花夕食, 创建于, 2002年)\n"
	"(朝花夕食, 创建于, 南京大学)\n"
	"---------------------\n"
	"待提取的文本内容：{text}\n"
	"三元组：\n"
)