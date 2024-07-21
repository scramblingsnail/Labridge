

PAPER_CHUNK_LEVEL_KEYWORD_EXTRACT_TEMPLATE_TMPL = (
	"Some text is provided below. Given the text, extract no more than {max_keywords} "
    "keywords from the text. Avoid stopwords."
    "---------------------\n"
    "{text}\n"
    "---------------------\n"
    "Provide keywords in the following comma-separated format: 'KEYWORDS: <keywords>'\n"
)