from llama_index.core.prompts.base import PromptTemplate, PromptType


MODIFY_COMMON_INFO_TMPL = (
"""
You have collected some information from the user, and the user comments on these information.
Here, several information and their descriptions are given as a dictionary in a JSON format,
with the information name as the keys, and their descriptions as the values.

Also, the corresponding collected results for these information is provided as a dictionary in a JSON format,
with the information name as the keys, and the collected contents as the values.

You should decide which information need modification according to the user's comment, and modify them .
Output the modified information as a dictionary in a JSON format STRICTLY,
with the information keys as keys and the corresponding information contents as values, 
You should use the provided information keys as the keys in your output dict.
DO NOT output any information that does not need modifications.
If all information do not need modification, output an empty dict: {{}}

The information keys & their descriptions:
{required_infos_str}

The information keys & corresponding collected contents:
{collected_infos_str}

The user's comment is as follows:
User: {user_comment_str}

Extra info:
{extra_info}

Answer:
"""
)

MODIFY_COMMON_INFO_PROMPT = PromptTemplate(
	MODIFY_COMMON_INFO_TMPL, prompt_type=PromptType.REFINE
)