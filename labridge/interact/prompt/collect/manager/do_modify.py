from llama_index.core.prompts.base import PromptTemplate, PromptType


DO_MODIFY_WORD = "yes"
NOT_MODIFY_WORD = "no"

WHETHER_MODIFY_INFO_TMPL = (
"""
You have collected some information from the user, and the user comments on these information.
Here, several information and their descriptions are given as a dictionary in a JSON format,
with the information name as the keys, and their descriptions as the values.

Also, the corresponding collected results for these information is provided as a dictionary in a JSON format,
with the information name as the keys, and the collected contents as the values.

You should judge whether the user tends to modify these collected contents, according to the user's response.
If the user wants to modify any information presented, please output <{do_modify_word}>.
If the user does not want to modify the presented information, or the user's comment is not relevant to the presented information,
please output <{not_modify_word}>.
You should not output anything beyond <{do_modify_word}> and <{not_modify_word}>.

The information keys & corresponding collected contents:
{collected_infos_str}

The user's comment is as follows:
User: {user_comment_str}

Whether user tends to modify these information:
"""
)

WHETHER_MODIFY_INFO_PROMPT = PromptTemplate(
	WHETHER_MODIFY_INFO_TMPL, prompt_type=PromptType.SINGLE_SELECT
)