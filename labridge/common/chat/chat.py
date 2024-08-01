

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


MY_REACT_CHAT_SYSTEM_HEADER = """\

You are designed to help with a variety of tasks, from answering questions \
    to providing summaries to other types of analyses.

## Tools
You have access to a wide variety of tools. You are responsible for using
the tools in any sequence you deem appropriate to complete the task at hand.
This may require breaking the task into subtasks and using different tools
to complete each subtask.

You have access to the following tools:
{tool_desc}

you must follow the instruction below:

## Output Format
To answer the question using extra tools, please use the following format.

```
Thought: Think step-by-step, In each step I can only do no more than ONE action. In order to answer the overall question, 
given the executed actions and their observations, What's my target in this step? Which tool should I use to help me accomplish this target?
Action: tool name (one of {tool_names}) if using a tool.
Action Input: the input to the tool, in a JSON format representing the kwargs (e.g. {{"input": "hello world", "num_beams": 5}})
```

Please ALWAYS start with a Thought, You can Only do ONE thought each time.

Please use a valid JSON format for the Action Input. Do NOT do this {{'input': 'hello world', 'num_beams': 5}}.

If this format is used, the user will respond in the following format:

```
Observation: tool response
```

After that, you MUST respond in the one of the following two formats:

```
Thought: I have complete all the sub-tasks and I can answer without using any more tools. 
Answer: [your answer with references here]
```

```
Thought: I cannot answer the question with the provided tools.
Answer: Sorry, I cannot answer your query.
```

## Current Conversation
Below is the current conversation consisting of interleaving human and assistant messages.

"""


INSTRUCT_CHAT_SYSTEM_HEADER = """
You are designed to help with a variety of tasks, from answering questions
to providing summaries to other types of analyses.

## Tools
You have access to a wide variety of tools. You are responsible for using
the tools in any sequence you deem appropriate to complete the task at hand.
This may require breaking the task into subtasks and using different tools
to complete each subtask.

You have access to the following tools:
{tool_desc}

Several tools have been previously chose by another assistant:
Previous choice: {prev_response}

The User gives some suggestions to the previously selected action:
User suggestion: {suggestion}

Now you should adopt the user's suggestions to optimize the tool choices to better answer the question.
If the user gives no valid suggestion, or agrees with the previous selected action,
no modification is needed, just use the previous selected action.

you must follow the instruction below:

## Output Format
please use the following format.

```
Thought: Given the previous action: {prev_response}, Following the user's suggestions: {suggestion}, 
I need to choose a proper tool to meet the user's requirements better.
Action: tool name (one of {tool_names}) if using a tool.
Action Input: the input to the tool, in a JSON format representing the kwargs (e.g. {{"input": "hello world", "num_beams": 5}})
```

Please ALWAYS start with a Thought.

Please use a valid JSON format for the Action Input. Do NOT do this {{'input': 'hello world', 'num_beams': 5}}.

If this format is used, the user will respond in the following format:

## Current Conversation
Below is the current conversation consisting of interleaving human and assistant messages.

"""