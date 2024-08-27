from llama_index.core.llms import LLM
from llama_index.core import Settings
from llama_index.core.embeddings import BaseEmbedding

from labridge.tools.base.function_base_tools import FunctionBaseTool, FuncOutputWithLog
from labridge.tools.interact.collect_and_authorize import CollectAndAuthorizeTool
from labridge.tools.base.tool_log import ToolLog, TOOL_OP_DESCRIPTION, TOOL_REFERENCES
from labridge.func_modules.memory.experiment.experiment_log import ExperimentLog
from labridge.callback.experiment_log.new_experiment import (
	CreateNewExperimentLogOperation,
	NEW_EXPERIMENT_REQUIRED_INFOS,
)

from labridge.callback.experiment_log.set_current_experiment import (
	SetCurrentExperimentOperation,
	SET_CURRENT_EXPERIMENT_REQUIRED_INFOS,
	CURRENT_EXPERIMENT_NAME_KEY,
	CURRENT_EXPERIMENT_DURATION_KEY,
)

from labridge.interact.collect.types.info_base import CollectingInfoBase
from labridge.interact.collect.types.common_info import CollectingCommonInfo
from labridge.interact.collect.types.select_info import CollectingSelectInfo
from labridge.callback.base.operation_log import OperationOutputLog, OP_DESCRIPTION, OP_REFERENCES

from typing import Any, Dict, Callable, List



COLLECT_NEW_EXPERIMENT_INFO_QUERY = (
	"来创建一个新的实验日志吧。"
)

NO_EXPERIMENT_MSG = (
	"您还没有任何的实验日志。"
)

SET_CURRENT_EXPERIMENT_MSG = (
	"您目前没有进行中的实验，先来设置一下当前进行的实验吧。请告诉我您现在在做哪一个实验？"
)

SET_CURRENT_EXPERIMENT_TAIL = (
	"好的，您在此期间的实验记录都会记录在该实验目录下。如果您更换了进行中的实验，请告知我。"
)


class CreateNewExperimentLogTool(CollectAndAuthorizeTool):
	r"""
	This tool is used to create a new experiment record in the user's experiment log storage.
	It is a `CollectAndAuthorizeTool` that needs information collection and authorization.

	Args:
		llm (LLM): The used LLM.
		embed_model (BaseEmbedding): The used embedding model.
		verbose (bool): Whether to show the inner progress.
	"""
	def __init__(
		self,
		llm: LLM = None,
		embed_model: BaseEmbedding = None,
		verbose: bool = False
	):
		super().__init__(
			tool_fn=self.create_new_experiment_log,
			tool_async_fn=self.acreate_new_experiment_log,
			tool_name=CreateNewExperimentLogTool.__name__,
			callback_operation=CreateNewExperimentLogOperation,
			llm=llm,
			embed_model=embed_model,
			verbose=verbose,
		)

	def required_info_dict(self) -> Dict[str, str]:
		r"""
		The required information.

		Returns:
			Dict[str, str]:

				- key: the information name.
				- value: the information description.
		"""
		return NEW_EXPERIMENT_REQUIRED_INFOS

	def required_infos(self) -> List[CollectingInfoBase]:
		r"""
		The required infos.

		Returns:
			List[CollectingInfoBase]:
				Return the packed info in CollectingInfoBase, such as `CollectingCommonInfo`.
		"""
		infos = []
		info_dict = self.required_info_dict()
		for key in info_dict.keys():
			common_info = CollectingCommonInfo(
				info_name=key,
				info_description=info_dict[key],
			)
			infos.append(common_info)
		return infos

	def create_new_experiment_log(
		self,
		user_id: str,
	) -> FuncOutputWithLog:
		r"""
		This tool is used to create a new experiment log record for the user.
		This tool is only used when the user asks for creating a new experiment log record, or other tools call this tool.

		Args:
			user_id (str): The user_id of a lab member.

		Returns:
			The tool's output and log.
		"""
		# This docstring is used as the tool description.
		return self.collect_and_authorize(
			user_id=user_id,
			query_str=COLLECT_NEW_EXPERIMENT_INFO_QUERY,
		)

	async def acreate_new_experiment_log(
		self,
		user_id: str,
	) -> FuncOutputWithLog:
		r"""
		This tool is used to create a new experiment log record for the user.
		This tool is only used when the user asks for creating a new experiment log record,
		or when other tools call this tool.

		Args:
			user_id (str): The user_id of a lab member.

		Returns:
			The tool's output and log.
		"""
		return await self.acollect_and_authorize(
			user_id=user_id,
			query_str=COLLECT_NEW_EXPERIMENT_INFO_QUERY,
		)


class SetCurrentExperimentTool(CollectAndAuthorizeTool):
	r"""
	This tool is used to set the experiment in progress for a user.

	Args:
		llm (LLM): The used LLM.
		embed_model (BaseEmbedding): The used embedding model.
		verbose (bool): Whether to show the inner progress.
	"""
	def __init__(
		self,
		llm: LLM = None,
		embed_model: BaseEmbedding = None,
		verbose: bool = False,
	):
		self.expr_log_store = None
		super().__init__(
			tool_fn=self.set_current_experiment,
			tool_async_fn=self.aset_current_experiment,
			tool_name=SetCurrentExperimentTool.__name__,
			callback_operation=SetCurrentExperimentOperation,
			llm=llm,
			embed_model=embed_model,
			verbose=verbose,
		)

	def required_info_dict(self) -> Dict[str, str]:
		r"""
		The required information.

		Returns:
			Dict[str, str]:

				- key: the information name.
				- value: the information description.
		"""
		return SET_CURRENT_EXPERIMENT_REQUIRED_INFOS

	def required_infos(self) -> List[CollectingInfoBase]:
		r"""
		The required infos.

		Returns:
			List[CollectingInfoBase]:
				Return the packed info in CollectingInfoBase, such as `CollectingCommonInfo` and `CollectingSelectInfo`.
		"""
		experiments = self.expr_log_store.get_all_experiments_with_description()
		select_name_info = CollectingSelectInfo(
			info_name=CURRENT_EXPERIMENT_NAME_KEY,
			info_description=self.required_info_dict()[CURRENT_EXPERIMENT_NAME_KEY],
			choices=experiments,
		)

		duration_info = CollectingCommonInfo(
			info_name=CURRENT_EXPERIMENT_DURATION_KEY,
			info_description=self.required_info_dict()[CURRENT_EXPERIMENT_DURATION_KEY]
		)
		return [select_name_info, duration_info]

	def set_experiment_log_store(self, user_id: str):
		r"""
		Load the user's experiment log storage.

		Args:
			user_id (str): The user_id of a lab member.
		"""
		if self.expr_log_store is None or self.expr_log_store.user_id != user_id:
			self.expr_log_store = ExperimentLog.from_user_id(
				user_id=user_id,
				embed_model=self._embed_model,
			)

	def set_current_experiment(
		self,
		user_id: str,
	) -> FuncOutputWithLog:
		r"""
		This tool is used to set the experiment in progress for the user, through interacting with the user.
		This tool is used ONLY when the user ask for setting his/her experiment in progress,
		or when other tools call this tool.

		Args:
			user_id (str): The user_id of a lab member.

		Returns:
			The tool output and log.
		"""
		# This docstring is used as tool description.
		self.set_experiment_log_store(user_id=user_id)

		expr_list = self.expr_log_store.get_all_experiments()

		if expr_list is None:
			create_tool = CreateNewExperimentLogTool(
				llm=self._llm,
				embed_model=self._embed_model,
			)
			create_tool.call(user_id=user_id)

		query_str = SET_CURRENT_EXPERIMENT_MSG
		output_log = self.collect_and_authorize(
			user_id=user_id,
			query_str=query_str,
		)

		# TODO Send to the user.
		print(SET_CURRENT_EXPERIMENT_TAIL)

		return output_log

	async def aset_current_experiment(
		self,
		user_id: str,
	) -> FuncOutputWithLog:
		r"""
		This tool is used to set the experiment in progress for the user, through interacting with the user.
		This tool is used ONLY when the user ask for setting his/her experiment in progress,
		or when other tools call this tool.

		Args:
			user_id (str): The user_id of a lab member.

		Returns:
			The tool output and log.
		"""
		self.set_experiment_log_store(user_id=user_id)
		expr_list = self.expr_log_store.get_all_experiments()
		if expr_list is None:
			create_tool = CreateNewExperimentLogTool(
				llm=self._llm,
				embed_model=self._embed_model,
			)
			await create_tool.acall(user_id=user_id)

		query_str = SET_CURRENT_EXPERIMENT_MSG
		output_log = await self.acollect_and_authorize(
			user_id=user_id,
			query_str=query_str,
		)

		# TODO Send to the user.
		print(SET_CURRENT_EXPERIMENT_TAIL)
		return output_log


class RecordExperimentLogTool(FunctionBaseTool):
	r"""
	This tool is used to record the experiment log for users.
	Use this tool When the user asks you to record anything about his/her experiment.

	- If the recorded experiment in progress is valid (That is, current time is not beyond this experiment's duration),
	the experiment log will be directly record to the record of the experiment in progress.
	- If the recorded experiment in progress is not valid, this tool will implicitly call the `SetCurrentExperimentTool`
	to set current experiment (Output the tool call requirement in the tool output.).

	Args:
		llm (LLM): The used LLM. If not specified, the `Settings.llm` will be used.
		embed_model (BaseEmbedding): The used embedding model. If not specified, the `Settings.embed_model` will be used.
		verbose (bool): Whether to show the inner progress.
	"""
	def __init__(
		self,
		llm: LLM = None,
		embed_model: BaseEmbedding = None,
		verbose: bool = False,
	):
		self._llm = llm or Settings.llm
		self._embed_model = embed_model or Settings.embed_model
		self._verbose = verbose
		super().__init__(
			fn=self.record_log,
			async_fn=self.arecord_log,
			tool_name=RecordExperimentLogTool.__name__,
		)

	def log(self, **kwargs: Any) -> ToolLog:
		r"""
		Record the tool log.

		Args:
			**kwargs (Any): The input keyword arguments and the (output, log) of the executed operation.

		Returns:

		"""
		op_log: str = kwargs["operation_log"]

		return ToolLog.construct(
			tool_name=self.metadata.name,
			tool_op_description=op_log,
		)

	def record_log(
		self,
		user_id: str,
		log_str: str,
	) -> FuncOutputWithLog:
		r"""
		This tool is used to record the experiment log of the experiment in progress for a user.

		If the no experiment record exists or experiment in progress is not valid, this tool will call
		the corresponding tools to help the user.

		Args:
			user_id (str): The user_id of a lab member.
			log_str (str): The experiment log to be recorded.

		Returns:
			The tool output and log.
		"""
		# This docstring is used as the tool description.
		expr_log_store = ExperimentLog.from_user_id(
			user_id=user_id,
			embed_model=self._embed_model,
		)

		# If no experiment log record exists.
		if expr_log_store.get_all_experiments() is None:
			create_tool = CreateNewExperimentLogTool(
				llm=self._llm,
				embed_model=self._embed_model,
			)
			create_tool.call(user_id=user_id)

		# If current experiment in progress is not valid.
		recent_expr = expr_log_store.get_recent_experiment()
		if recent_expr is None:
			set_tool = SetCurrentExperimentTool(
				llm=self._llm,
				embed_model=self._embed_model,
			)
			set_tool.call(user_id=user_id)

			# reload
			expr_log_store = ExperimentLog.from_user_id(
				user_id=user_id,
				embed_model=self._embed_model,
			)
			recent_expr = expr_log_store.get_recent_experiment()

		expr_log_store.put(
			experiment_name=recent_expr,
			log_str=log_str,
		)
		expr_log_store.persist()
		op_log_str = (
			f"Have put a new experiment log into the experiment log store of the user: {user_id}.\n" 
			f"Experiment name: {recent_expr}\n"
		)
		return FuncOutputWithLog(
			fn_output=f"Have record the log {log_str}",
			fn_log={"operation_log": op_log_str}
		)

	async def arecord_log(
		self,
		user_id: str,
		log_str: str,
	) -> FuncOutputWithLog:
		r"""
		This tool is used to record the experiment log of the experiment in progress for a user.

		If the no experiment record exists or experiment in progress is not valid, this tool will call
		the corresponding tools to help the user.

		Args:
			user_id (str): The user_id of a lab member.
			log_str (str): The experiment log to be recorded.

		Returns:
			The tool output and log.
		"""
		# This docstring is used as the tool description.
		expr_log_store = ExperimentLog.from_user_id(
			user_id=user_id,
			embed_model=self._embed_model,
		)

		# If no experiment log record exists.
		if expr_log_store.get_all_experiments() is None:
			create_tool = CreateNewExperimentLogTool(
				llm=self._llm,
				embed_model=self._embed_model,
			)
			await create_tool.acall(user_id=user_id)

		# If current experiment in progress is not valid.
		recent_expr = expr_log_store.get_recent_experiment()
		if recent_expr is None:
			set_tool = SetCurrentExperimentTool(
				llm=self._llm,
				embed_model=self._embed_model,
			)
			await set_tool.acall(user_id=user_id)

			# reload
			expr_log_store = ExperimentLog.from_user_id(
				user_id=user_id,
				embed_model=self._embed_model,
			)
			recent_expr = expr_log_store.get_recent_experiment()

		expr_log_store.put(
			experiment_name=recent_expr,
			log_str=log_str,
		)
		expr_log_store.persist()
		op_log_str = (
			f"Have put a new experiment log into the experiment log store of the user: {user_id}.\n" 
			f"Experiment name: {recent_expr}\n"
		)
		return FuncOutputWithLog(
			fn_output=f"Have record the log {log_str}",
			fn_log={"operation_log": op_log_str}
		)


if __name__ == "__main__":
	from labridge.llm.models import get_models
	import asyncio

	llm, embed_model = get_models()
	Settings.llm = llm
	Settings.embed_model = embed_model

	# create_tool = CreateNewExperimentLogTool()
	# print(create_tool.metadata.name)
	# tool_log = create_tool.call(user_id="杨再正")
	# print(tool_log)

	# set_tool = SetCurrentExperimentTool()
	# print(set_tool.metadata.name)
	# tool_log = set_tool.call(user_id="杨再正")
	# print(tool_log)

	record_tool= RecordExperimentLogTool()
	print(record_tool.metadata.name)
	tool_log = record_tool.call(user_id="杨再正", log_str="开始Debug React")
	print(tool_log)

	# async def main():
	# 	# create_task = asyncio.create_task(create_tool.acall(user_id="杨再正"))
	# 	# await create_task
	#
	# 	set_task = asyncio.create_task(record_tool.acall(user_id="杨再正", log_str="完成代码的原理性验证"))
	# 	await set_task
	# asyncio.run(main())


