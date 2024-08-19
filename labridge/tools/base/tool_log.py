import json


TOOL_OP_DESCRIPTION = "operation_description"
TOOL_REFERENCES = "references"

LOG_TO_SYSTEM_KEYS = [
	TOOL_OP_DESCRIPTION,
	TOOL_REFERENCES,
]


from typing import Optional, Dict, List, Union


class ToolLog(object):
	r"""
	This class record the log of a specific tool.
	The `log_to_user` and `references` in `log_to_system` will be presented to the users.

	Args:
		tool_name (str): The tool name.
		log_to_user (str): This log might be presented to the users.
		log_to_system (dict): This log is more structured, specifically, it is a dictionary in JSON format.
			The keys 'operation_description' and 'references' are required. The values of `references` are either
			None or List[str], where the `str` is in JSON format.
	"""
	def __init__(
		self,
		tool_name: str,
		log_to_user: Optional[str],
		log_to_system: Dict[str, Union[str, Optional[List[str]]]]

	):
		self.tool_name = tool_name
		self.log_to_user = log_to_user

		for key in LOG_TO_SYSTEM_KEYS:
			if key not in log_to_system.keys():
				raise ValueError(f"The key {key} is required in the log_to_system.")

		ref = log_to_system[TOOL_REFERENCES]
		if ref and not isinstance(ref, list):
			raise ValueError(f"The value of '{TOOL_REFERENCES}' can only be list or None.")
		self.log_to_system = log_to_system

	@classmethod
	def construct(
		cls,
		tool_name: str,
		tool_op_description: str,
		tool_references: Optional[List[str]] = None,
		log_to_user: str = None,
	):
		return cls(
			tool_name=tool_name,
			log_to_user=log_to_user,
			log_to_system={
				TOOL_OP_DESCRIPTION: tool_op_description,
				TOOL_REFERENCES: tool_references,
			}
		)

	def dumps(self) -> str:
		r"""
		Dump to a string.

		Returns:
			str: the dumped string.
		"""
		logs = {
			"tool_name": self.tool_name,
			"log_to_user": self.log_to_user,
			"log_to_system": self.log_to_system,
		}
		return json.dumps(logs)

	@classmethod
	def loads(
		cls,
		log_str: str,
	):
		r"""
		Load from a string.

		Args:
			log_str (str): The dumped string of a ToolLog object.

		Returns:
			The loaded ToolLog object.
		"""
		try:
			logs = json.loads(log_str)
			tool_name = logs["tool_name"]
			log_to_user = logs["log_to_user"]
			log_to_system = logs["log_to_system"]
			return cls(
				tool_name=tool_name,
				log_to_user=log_to_user,
				log_to_system=log_to_system,
			)
		except Exception:
			raise ValueError("Invalid tool log string.")
