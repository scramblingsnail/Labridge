from llama_index.core.prompts.base import PromptTemplate, PromptType


COLLECT_COMMON_INFO_TMPL = (
"""
You are collecting some information from the user's response.
The user's response might not include all of the information, 
try to extract as more valid information mentioned above as you can.

The required information keys and their descriptions are given as a dictionary in a JSON format,
with the information names as keys and the corresponding descriptions as values.

You should output the extracted information as a dictionary in a JSON format STRICTLY,
with the information keys as keys and the corresponding extracted information as values, 
You should use the provided information keys as the keys in your output dict.

Example:
Information keys & descriptions: {{"gender": "用户的性别", "age": "用户的年龄", "name": "用户的姓名", "title": "用户所给文章的标题"}}
User's response: <response>
Answer:
{{"gender": "男", "age": 22, "title": "A comprehensive survey to computer architecture", "name": null}}

If some information are not provided in the user's response, you should set the corresponding value to null.
Please output valid extracted information, DO NOT output these examples above:
{{"gender": "男", "age": 22, "title": "A comprehensive survey to computer architecture", "name": null}}

Here is some Extra prompt: 
{extra_info}

Let's try this now, the information to be extracted and the user's response are shown below:

Information keys & descriptions: {required_infos_str}
User's response: {user_response_str}
Answer:
"""
)

COLLECT_COMMON_INFO_PROMPT = PromptTemplate(
    COLLECT_COMMON_INFO_TMPL, prompt_type=PromptType.SCHEMA_EXTRACT
)