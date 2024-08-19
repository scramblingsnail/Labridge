import time
import json

from llama_index.core.prompts.base import PromptTemplate, PromptType
from llama_index.core.llms import LLM
from llama_index.core.settings import Settings
from llama_index.core.embeddings import BaseEmbedding
from typing import Any

import labridge.callback as callback
from labridge.callback.base.operation_log import OperationOutputLog, OP_DESCRIPTION, OP_REFERENCES

from labridge.callback import CALL_BACK_OPS, CallBackOperationBase
from labridge.interact.prompt.authorize.analyze_agree import (
	AUTHORIZATION_ANALYZE_PROMPT,
	ANALYZE_AGREE_WORD,
	ANALYZE_DISAGREE_WORD,
)


STRICT_AGREE_WORDS = [
	"yes",
	"ok",
	"是",
]

AUTHORIZE_QUERY_TMPL = \
"""
我将为您执行如下操作，请问您希望执行该操作吗？

**操作描述：**
{operation_description}
"""

STRICT_AUTHORIZE_QUERY_TMPL = \
"""
我将为您执行一项重要操作，如果您同意该操作，请回答如下指令之一：
{strict_agree_str}

**操作描述：**
{operation_description}
"""

def analyze_agree(llm_response: str) -> bool:
	llm_str = filter(lambda x: x.isalpha(), [char for char in llm_response])
	llm_str = "".join(llm_str)
	return llm_str == ANALYZE_AGREE_WORD


def operation_authorize(
	user_id: str,
	op_name: str,
	kwargs_str: str,
	authorize_strict_mode: bool = False,
	llm: LLM = None,
	embed_model: BaseEmbedding = None,
	verbose: bool = False,
) -> OperationOutputLog:
	r"""
	This function is used to query the user whether to execute a specific operation.

	Args:
		user_id (str): The user that will make decisions.
		op_name (str): The operation to be executed.
		kwargs_str (str): The keyword arguments of the operation function, which is dumped as a json string.
		authorize_strict_mode (bool): If it is set to True, the operation will be executed only when the user response
			the `STRICT_AGREE_WORDS`. Defaults to False.
		llm (LLM): The used LLM. Defaults to None. If set to None, the Settings.llm will be used.
		embed_model (BaseEmbedding): The used embedding model. Defaults to None.
			If set to None, the Settings.embed_model will be used.
		verbose (str): Whether to show the progress.

	Returns:
		callback_log (str): the log string.

	"""
	if op_name not in CALL_BACK_OPS:
		raise ValueError(f"{op_name} is not a valid callback operation name.")

	operation_class = getattr(callback, op_name)
	if not issubclass(operation_class, CallBackOperationBase):
		raise ValueError(f"{op_name} should be a subclass of 'CallBackOperationBase'.")

	llm = llm or Settings.llm
	embed_model = embed_model or Settings.embed_model

	operation = operation_class(
		llm=llm,
		embed_model=embed_model,
		verbose=verbose,
	)

	kwargs = json.loads(kwargs_str)
	op_description = operation.operation_description(**kwargs)
	if authorize_strict_mode:
		query_str = STRICT_AUTHORIZE_QUERY_TMPL.format(
			strict_agree_str=",".join(STRICT_AGREE_WORDS),
			operation_description=op_description,
		)
	else:
		query_str = AUTHORIZE_QUERY_TMPL.format(operation_description=op_description)

	# TODO: send the operation description to the user.
	print(query_str)

	# TODO: wait the user response.
	user_response = input("User: ")

	agree = False
	if authorize_strict_mode:
		if user_response.encode("utf-8").isalpha():
			user_response = user_response.lower()
		agree = user_response in STRICT_AGREE_WORDS
	else:
		judgement = llm.predict(
			prompt=AUTHORIZATION_ANALYZE_PROMPT,
			agree_word=ANALYZE_AGREE_WORD,
			disagree_word=ANALYZE_DISAGREE_WORD,
			user_response=user_response,
		)
		agree = analyze_agree(llm_response=judgement)

	if agree:
		# TODO: I need an operation buffer to store operations.
		callback_log = operation.do_operation(**kwargs)
		return callback_log
	else:
		callback_log_str = (
			f"The assistant tries to obtain the authorization from user {user_id} to perform an operation."
			f"The user disagreed, so this operation does not be performed.\n"
			f"The operation is described as follows:\n{op_description}\n\n"
			f"The user's response is as follows:\n{user_response}"
		)
		return OperationOutputLog(
			operation_name=op_name,
			operation_output=callback_log_str,
			log_to_user=None,
			log_to_system={
				OP_DESCRIPTION: callback_log_str,
				OP_REFERENCES: None,
			},
		)


async def aoperation_authorize(
	user_id: str,
	op_name: str,
	kwargs_str: str,
	authorize_strict_mode: bool = False,
	llm: LLM = None,
	embed_model: BaseEmbedding = None,
	verbose: bool = False,
) -> OperationOutputLog:
	r"""
	This function is used to query the user whether to execute a specific operation.

	Args:
		user_id (str): The user that will make decisions.
		op_name (str): The operation to be executed.
		kwargs_str (str): The keyword arguments of the operation function, which is dumped as a json string.
		authorize_strict_mode (bool): If it is set to True, the operation will be executed only when the user response
			the `STRICT_AGREE_WORDS`. Defaults to False.
		llm (LLM): The used LLM. Defaults to None. If set to None, the Settings.llm will be used.
		embed_model (BaseEmbedding): The used embedding model. Defaults to None.
			If set to None, the Settings.embed_model will be used.
		verbose (str): Whether to show the progress.

	Returns:
		callback_log (str): the log string.

	"""
	if op_name not in CALL_BACK_OPS:
		raise ValueError(f"{op_name} is not a valid callback operation name.")

	operation_class = getattr(callback, op_name)
	if not issubclass(operation_class, CallBackOperationBase):
		raise ValueError(f"{op_name} should be a subclass of 'CallBackOperationBase'.")

	llm = llm or Settings.llm
	embed_model = embed_model or Settings.embed_model

	operation = operation_class(
		llm=llm,
		embed_model=embed_model,
		verbose=verbose,
	)
	kwargs = json.loads(kwargs_str)
	op_description = operation.operation_description(**kwargs)
	if authorize_strict_mode:
		query_str = STRICT_AUTHORIZE_QUERY_TMPL.format(
			strict_agree_str=",".join(STRICT_AGREE_WORDS),
			operation_description=op_description,
		)
	else:
		query_str = AUTHORIZE_QUERY_TMPL.format(operation_description=op_description)

	# TODO: send the operation description to the user.
	print(query_str)

	# TODO: wait the user response.
	user_response = input("User: ")

	agree = False
	if authorize_strict_mode:
		if user_response.encode("utf-8").isalpha():
			user_response = user_response.lower()
		agree = user_response in STRICT_AGREE_WORDS
	else:
		judgement = await llm.apredict(
			prompt=AUTHORIZATION_ANALYZE_PROMPT,
			agree_word=ANALYZE_AGREE_WORD,
			disagree_word=ANALYZE_DISAGREE_WORD,
			user_response=user_response,
		)
		agree = analyze_agree(llm_response=judgement)

	if agree:
		# TODO: I need an operation buffer to store operations. two operation class: 1. real time, 2. buffer.
		callback_log = operation.do_operation(**kwargs)
		return callback_log
	else:
		callback_log_str = (f"The assistant tries to obtain the authorization from user {user_id} to perform an operation."
						f"The user disagreed, so this operation does not be performed.\n"
						f"The operation is described as follows:\n{op_description}\n\n"
						f"The user's response is as follows:\n{user_response}")
		return OperationOutputLog(
			operation_name=op_name,
			operation_output=callback_log_str,
			log_to_user=None,
			log_to_system={
				OP_DESCRIPTION: callback_log_str,
				OP_REFERENCES: None,
			},
		)
