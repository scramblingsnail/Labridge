from llama_index.core.llms import LLM
from llama_index.core.embeddings import BaseEmbedding
from llama_index.core import Settings
from labridge.func_modules.memory.experiment.experiment_log import ExperimentLog

from labridge.callback.base.operation_log import OperationOutputLog, OP_DESCRIPTION, OP_REFERENCES
from labridge.callback.base.operation_base import CallBackOperationBase
from labridge.common.utils.time import get_time, str_to_datetime, str_to_delta_time, datetime_to_str



SET_CURRENT_EXPERIMENT_DESCRIPTION = (
"""
将 {user_id} 进行中的实验修改为：

**实验名称:** {experiment_name}
**开始时间:** {start_date}, {start_time}
**预期结束时间:** {end_date}, {end_time}
"""
)


CURRENT_EXPERIMENT_NAME_KEY = "experiment_name"
CURRENT_EXPERIMENT_DURATION_KEY = "experiment_duration"

SET_CURRENT_EXPERIMENT_REQUIRED_INFOS = {
	CURRENT_EXPERIMENT_NAME_KEY: "The name of the experiment that will be in progress",
	CURRENT_EXPERIMENT_DURATION_KEY: "The duration of the experiment in progress, "
									   "it MUST be transformed to the following FORMAT: <Hours>h:<Minutes>m:<Seconds>s",
}


class SetCurrentExperimentOperation(CallBackOperationBase):
	r"""
	This operation will set a recorded experiment as the user's experiment in progress.

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
		op_name: str = None,
	):

		llm = llm or Settings.llm
		embed_model = embed_model or Settings.embed_model
		super().__init__(
			llm=llm,
			embed_model=embed_model,
			verbose=verbose,
			op_name=op_name or SetCurrentExperimentOperation.__name__,
		)

	def operation_description(self, **kwargs) -> str:
		r"""
		Return the operation description, this description will be sent to the user for authorization.

		Args:
			user_id (str): The user id of a lab member.
			experiment_name (str): The name of a recorded experiment.
			experiment_duration (str): The duration of the experiment, in a format of "%Hh%Mm%Ss",
				refer to `common.utils.time`.

		Returns:
			str: The operation description.
		"""
		user_id = kwargs["user_id"]
		experiment_name = kwargs["experiment_name"]
		experiment_duration = kwargs["experiment_duration"]

		start_date, start_time = get_time()
		start = str_to_datetime(date_str=start_date, time_str=start_time)
		delta_time = str_to_delta_time(time_str=experiment_duration)
		end = start + delta_time
		end_date, end_time = datetime_to_str(date_time=end)
		op_description = SET_CURRENT_EXPERIMENT_DESCRIPTION.format(
			user_id=user_id,
			experiment_name=experiment_name,
			start_date=start_date,
			start_time=start_time,
			end_date=end_date,
			end_time=end_time,
		)
		return op_description

	def do_operation(self, **kwargs) -> OperationOutputLog:
		r"""
		Execute the operation set the experiment in progress for a user.

		Args:
			user_id (str): The user id of a lab member.
			experiment_name (str): The name of a recorded experiment.
			experiment_duration (str): The duration of the experiment, in a format of "%Hh%Mm%Ss",
				refer to `common.utils.time`.

		Returns:
			OperationOutputLog: The output and log of the operation.
		"""
		user_id = kwargs["user_id"]
		experiment_name = kwargs["experiment_name"]
		experiment_duration = kwargs["experiment_duration"]

		start_date, start_time = get_time()
		start = str_to_datetime(date_str=start_date, time_str=start_time)
		delta_time = str_to_delta_time(time_str=experiment_duration)
		end = start + delta_time
		end_date, end_time = datetime_to_str(date_time=end)

		expr_log_store = ExperimentLog.from_user_id(
			user_id=user_id,
			embed_model=self._embed_model
		)
		expr_log_store.set_recent_experiment(
			experiment_name=experiment_name,
			start_date=start_date,
			start_time=start_time,
			end_date=end_date,
			end_time=end_time,
		)
		expr_log_store.persist()
		op_log_str = (
			f"Set the experiment in progress for {user_id}.\n"
			f"Experiment name: {experiment_name}.\n"
			f"Start from {start_date}, {start_time} to {end_date}, {end_time}."
		)
		return OperationOutputLog(
			operation_name=self.op_name,
			operation_output=None,
			log_to_user=None,
			log_to_system={
				OP_DESCRIPTION: op_log_str,
				OP_REFERENCES: None,
			}
		)

	async def ado_operation(self, **kwargs) -> OperationOutputLog:
		return self.do_operation(**kwargs)