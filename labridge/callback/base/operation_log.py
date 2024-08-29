import json


OP_DESCRIPTION = "operation_description"
OP_REFERENCES = "references"

LOG_TO_SYSTEM_KEYS = [
	OP_DESCRIPTION,
	OP_REFERENCES,
]


from typing import Optional, Dict, List, Union


class OperationOutputLog(object):
	r"""
	This class record the log of a specific callback operation.
	The `operation_output` will be a part of the corresponding tool output.
	The `log_to_user` and `references` in `log_to_system` will be presented to the users.

	Args:
		operation_name (str): The operation name.
		operation_output (str): The operation output.
		log_to_user (str): This log might be presented to the users.
		log_to_system (dict): This log is more structured, specifically, it is a dictionary in JSON format.
			The keys 'operation_description' and 'references' are required. The values of `references` are either
			None or List[str], where the `str` is in JSON format, for example, the dumped string of a `PaperInfo`.
	"""
	def __init__(
		self,
		operation_name: str,
		operation_output: Optional[str],
		log_to_user: Optional[str],
		log_to_system: Dict[str, Union[str, Optional[List[str]]]],
		operation_abort: Optional[bool] = False,

	):
		self.operation_name = operation_name
		self.operation_output = operation_output
		self.log_to_user = log_to_user
		self.operation_abort = operation_abort

		for key in LOG_TO_SYSTEM_KEYS:
			if key not in log_to_system.keys():
				raise ValueError(f"The key {key} is required in the log_to_system.")

		ref = log_to_system[OP_REFERENCES]
		if ref and not isinstance(ref, list):
			raise ValueError(f"The value of '{OP_REFERENCES}' can only be list or None.")
		self.log_to_system = log_to_system

	@classmethod
	def construct(
		cls,
		operation_name: str,
		operation_output: str,
		op_description: str,
		op_references: Optional[List[str]] = None,
		log_to_user: Optional[str] = None,
		operation_abort: Optional[bool] = False,
	):
		return cls(
			operation_name=operation_name,
			operation_output=operation_output,
			log_to_user=log_to_user,
			log_to_system={
				OP_DESCRIPTION: op_description,
				OP_REFERENCES: op_references,
			},
			operation_abort = operation_abort,
		)

	def dumps(self) -> str:
		r""" Dump to JSON string. """
		output_logs = {
			"operation_name": self.operation_name,
			"operation_output": self.operation_output,
			"log_to_user": self.log_to_user,
			"log_to_system": self.log_to_system,
			"operation_abort": self.operation_abort
		}
		return json.dumps(output_logs)

	@classmethod
	def loads(
		cls,
		log_str: str,
	):
		r""" Load from JSON string. """
		try:
			output_logs = json.loads(log_str)
			operation_name = output_logs["operation_name"]
			operation_output = output_logs["operation_output"]
			log_to_user = output_logs["log_to_user"]
			log_to_system = output_logs["log_to_system"]
			operation_abort = output_logs["operation_abort"]
			return cls(
				operation_name=operation_name,
				operation_output=operation_output,
				log_to_user=log_to_user,
				log_to_system=log_to_system,
				operation_abort=operation_abort,
			)
		except Exception:
			raise ValueError("Invalid operation log string.")

