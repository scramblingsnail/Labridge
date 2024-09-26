from llama_index.core.embeddings import BaseEmbedding
from llama_index.core import Settings
from llama_index.core.llms import LLM
from labridge.callback.base.operation_base import CallBackOperationBase
from labridge.callback.base.operation_log import OperationOutputLog, OP_DESCRIPTION, OP_REFERENCES
from labridge.func_modules.paper.store.temporary_store import RecentPaperStore
from labridge.func_modules.reference.paper import PaperInfo


class XYPlatformOperation(CallBackOperationBase):
	r"""
	This tool will operate a XYPlatform in real world.

	"""
	def __init__(
		self,
		llm: LLM = None,
		embed_model: BaseEmbedding = None,
		verbose: bool = False,
		op_name: str = None,
	):
		embed_model = embed_model or Settings.embed_model
		llm = llm or Settings.llm
		super().__init__(
			embed_model=embed_model,
			llm=llm,
			verbose=verbose,
			op_name=XYPlatformOperation.__name__,
		)

	def operation_description(self, **kwargs) -> str:
		r"""
		Return the operation description, this description will be sent to the user for authorization.

		Args:
			x_direction (int): An integer representing the moving direction in `x` axis. 0 means moving to left, 1 means moving to right.
			x_movement (int): The distance moved along `x` axis. unit: milimeter.
			y_direction (int): An integer representing the moving direction in `y` axis. 0 means moving down, 1 means moving up.
			y_movement (int): The distance moved along `y` axis. unit: milimeter.

		Returns:
			str: The operation description.
		"""
		x_dir = kwargs.get("x_direction", None)
		x_move = kwargs.get("x_movement", 0)
		y_dir = kwargs.get("y_direction", None)
		y_move = kwargs.get("y_movement", 0)

		if x_move <= 0 and y_move <= 0:
			dsc_str = "不进行移动操作。"
			return dsc_str

		if x_dir is None and y_dir is None:
			raise ValueError("For a valid operation of the XY Platform, the `x_dir` and `y_dir` cannot both be None.")

		dsc_str = "将XY双轴电动位移台"
		if x_dir is not None and x_move > 0:
			x_dir_str = "右" if x_dir > 0 else "左"
			dsc_str += f"沿x轴方向向{x_dir_str}移动{x_move}毫米。"

		if y_dir is not None and y_move > 0:
			y_dir_str = "上" if y_dir > 0 else "下"
			dsc_str += f"沿y轴方向向{y_dir_str}移动{y_move}毫米。"
		return dsc_str

	def do_operation(self, **kwargs) -> OperationOutputLog:
		x_dir = kwargs.get("x_direction", None)
		x_move = kwargs.get("x_movement", 0)
		y_dir = kwargs.get("y_direction", None)
		y_move = kwargs.get("y_movement", 0)

		op_log = self.operation_description(**kwargs)
		return OperationOutputLog(
			operation_name=self.op_name,
			operation_output=None,
			log_to_user=None,
			log_to_system={
				OP_DESCRIPTION: op_log,
				OP_REFERENCES: None,
			}
		)

	async def ado_operation(self, **kwargs) -> OperationOutputLog:
		return self.do_operation(**kwargs)




