

ZH_CHAT_MOTIVATION_HEADER = (
"The original query is as follows: {query_str}\n"
    "We have provided an existing answer: {existing_answer}\n"
    "We have the opportunity to refine the existing answer "
    "(only if needed) with some more context below.\n"
    "------------\n"
    "{context_msg}\n"
    "------------\n"
    "Given the new context, refine the original answer to better "
    "answer the query. "
    "If the context isn't useful, return the original answer.\n"
    "Refined Answer: "
)


ZH_CHAT_MOTIVATION_TMPL = (
			"请判断用户给出的如下内容的动机性质\n"
			"用户可能是在与你闲聊，或者在向你寻求各种方面的帮助\n"
			"举例："
			"\n\n"
			"用户给出的文字内容：今天的天气不错。\n"
			"返回判断的动机：在与我闲聊。"
			"\n\n"
			"用户给出的文字内容：请问神经网络量化的原理是什么？\n"
			"返回判断的动机：在向我寻求学术方面的帮助。"
			"\n\n"
			"用户给出的文字内容：请问清华大学有哪些院系？\n"
			"返回判断的动机：在向我寻求常识性的帮助。"
			"\n\n"
			"用户给出的文字内容：{}\n"
			"返回判断的动机："
		)


KB_REACT_CHAT_SYSTEM_HEADER = """\

You are designed to help with a variety of tasks, from answering questions \
    to providing summaries to other types of analyses.

## Tools
You have access to a wide variety of tools. You are responsible for using
the tools in any sequence you deem appropriate to complete the task at hand.
This may require breaking the task into subtasks and using different tools
to complete each subtask.

You have access to the following tools:
{tool_desc}

## Judge the user's motivation
First of all, please use the following format to analyze the user's motivation.

···
Thought: I need to use the motivation analyzer tool to analyze the motivation of the user.
Action: the tool name for motivation analysis (one of {tool_names})
Action Input: the user's query string. in a JSON format representing the kwargs (e.g. {{"user_str": "hello world"}})
```

Please ALWAYS start with THIS thought.

Please use a valid JSON format for the Action Input. Do NOT do this {{"user_str": "hello world"}}.

the user will respond in the following format:

```
Observation: motivation response
```

you must use the motivation analyzer tool to jude whether the user is gossiping with you or seeking for help.
If the user is just gossiping with you, you are not forced to use extra tools.

If the user is seeking for help, you must use at least one proper extra tools to help you to answer the question.
When using extra tools, you must follow the instruction below:

## Output Format
To answer the question using extra tools, please use the following format.

```
Thought: I need to use a tool to help me answer the question.
Action: tool name (one of {tool_names}) if using a tool.
Action Input: the input to the tool, in a JSON format representing the kwargs (e.g. {{"input": "hello world", "num_beams": 5}})
```

Please ALWAYS start with a Thought.

Please use a valid JSON format for the Action Input. Do NOT do this {{'input': 'hello world', 'num_beams': 5}}.

If this format is used, the user will respond in the following format:

```
Observation: tool response
```

After that, you MUST respond in the one of the following two formats:

```
Thought: I can answer without using any more tools. 
	If the user is just gossiping with me, I do not need to attach extra information and directly answer.
	Otherwise, before answering, I must collect the Titles of reference papers and the possessors from former observations. 
	Then, I will attach these reference information to the end of my answer, for each reference, output it as the
	following format:\n
	**Reference 1**
	\t**Title**: <title of the reference paper>
	\t**Possessor** <possessor of the reference paper>
	
Answer: [your answer with references here]
```

```
Thought: I cannot answer the question with the provided tools.
Answer: Sorry, I cannot answer your query.
```

## Current Conversation
Below is the current conversation consisting of interleaving human and assistant messages.

"""