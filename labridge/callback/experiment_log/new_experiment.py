from llama_index.core.embeddings import BaseEmbedding
from llama_index.core.llms import LLM
from llama_index.core import Settings

from labridge.callback.base.operation_base import CallBackOperationBase
from labridge.callback.base.operation_log import OperationOutputLog, OP_DESCRIPTION, OP_REFERENCES
from labridge.func_modules.memory.experiment.experiment_log import ExperimentLog


NEW_EXPERIMENT_NAME_KEY = "experiment_name"
NEW_EXPERIMENT_DESCRIPTION_KEY = "experiment_description"

NEW_EXPERIMENT_REQUIRED_INFOS = {
	NEW_EXPERIMENT_NAME_KEY: "The name of the new experiment",
	NEW_EXPERIMENT_DESCRIPTION_KEY: "The description of the new experiment",
}


CREATE_NEW_EXPERIMENT_DESCRIPTION = (
"""
为 {user_id} 创建新的实验日志记录。

**实验名称:** {experiment_name}
**实验描述:**
	{experiment_description}
"""
)


class CreateNewExperimentLogOperation(CallBackOperationBase):
	r"""
	This operation will create a new experiment record for a specific user.

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
		embed_model = embed_model or Settings.embed_model
		self.op_name = CreateNewExperimentLogOperation.__name__
		llm = llm or Settings.llm
		super().__init__(
			llm=llm,
			embed_model=embed_model,
			verbose=verbose,
		)

	def operation_description(self, **kwargs) -> str:
		r"""
		Return the operation description, this description will be sent to the user for authorization.

		Args:
			user_id (str): The user id of a lab member.
			experiment_name (str): The name of the new experiment.
			experiment_description (str): The description of the new experiment.

		Returns:
			str: The operation description.
		"""
		user_id = kwargs["user_id"]
		expr_name = kwargs[NEW_EXPERIMENT_NAME_KEY]
		expr_description = kwargs[NEW_EXPERIMENT_DESCRIPTION_KEY]

		op_description = CREATE_NEW_EXPERIMENT_DESCRIPTION.format(
			user_id=user_id,
			experiment_name=expr_name,
			experiment_description=expr_description,
		)
		return op_description

	def do_operation(self, **kwargs) -> OperationOutputLog:
		r"""
		Execute the operation to add a new experiment record.

		Args:
			user_id (str): The user id of a lab member.
			experiment_name (str): The name of the new experiment.
			experiment_description (str): The description of the new experiment.

		Returns:
			OperationOutputLog: The output and log of the operation.
		"""
		user_id = kwargs["user_id"]
		expr_name = kwargs[NEW_EXPERIMENT_NAME_KEY]
		expr_description = kwargs[NEW_EXPERIMENT_DESCRIPTION_KEY]
		expr_log_store = ExperimentLog.from_user_id(
			user_id=user_id,
			embed_model=self._embed_model,
		)

		expr_log_store.create_experiment(
			experiment_name=expr_name,
			description=expr_description,
		)
		expr_log_store.persist()

		op_log_str = (
			f"Have created a new experiment log record for the user {user_id}.\n"
			f"Experiment name: {expr_name}"
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
