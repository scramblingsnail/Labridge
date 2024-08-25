import json

from inspect import signature
from llama_index.core.bridge.pydantic import (
	BaseModel,
	FieldInfo,
	create_model,
)
from typing import (
	Any,
	Callable,
	List,
	Optional,
	Tuple,
	Type,
	Union,
	cast,
	Dict,
)

import labridge.func_modules.reference as reference
from labridge.tools.base.tool_log import ToolLog, TOOL_REFERENCES, TOOL_OP_DESCRIPTION
from labridge.func_modules.reference.base import REF_TYPE, RefInfoBase
from labridge.func_modules.reference.paper import PaperInfo
from labridge.tools.paper.global_papers.utils import ref_papers_str_to_user, ref_papers_file_path


REF_INFO_TO_STR_FUNC_DICT = {
	PaperInfo.__name__: ref_papers_str_to_user,
}

REF_INFO_TO_FILE_PATH_FUNC_DICT = {
	PaperInfo.__name__: ref_papers_file_path,
}



def pack_tool_output(tool_output: str, tool_log: str = None) -> str:
	r"""
	Pack the tool output and tool log in a dict and dump to string.

	Args:
		tool_output (str): The tool output string.
		tool_log (str): The tool log string.

	Returns:
		The dumped tool output and log.
	"""
	tool_out_dict = {
		"tool_output": tool_output,
		"tool_log": tool_log,
	}
	tool_out_str = json.dumps(tool_out_dict)
	return tool_out_str


def unpack_tool_output(tool_out_json: str) -> Tuple[str, Optional[str]]:
	r"""
	Unpack the tool output string and tool log string from

	Args:
		tool_out_json:

	Returns:

	"""
	try:
		tool_out_dict = json.loads(tool_out_json)
		tool_output, tool_log = tool_out_dict["tool_output"], tool_out_dict["tool_log"]
		return tool_output, tool_log
	except Exception:
		return tool_out_json, None


def get_all_ref_info(tool_logs: List[ToolLog]) -> Dict[str, RefInfoBase]:
	extra_refs_dict = dict()

	for log in tool_logs:
		log_to_system = log.log_to_system
		if log_to_system is not None and log_to_system[TOOL_REFERENCES] is not None:
			refs = log_to_system[TOOL_REFERENCES]
			for ref_str in refs:
				ref_dict = json.loads(ref_str)
				# RefInfo type
				ref_type = ref_dict[REF_TYPE]
				ref_class = getattr(reference, ref_type)
				# Load RefInfo
				ref_info = ref_class.loads(ref_str)
				this_type_refs = extra_refs_dict.get(ref_type, [])
				this_type_refs.append(ref_info)
				extra_refs_dict[ref_type] = this_type_refs
	return extra_refs_dict


def get_ref_file_paths(tool_logs: List[ToolLog]) -> List[str]:
	r"""

	"""
	extra_refs_dict = get_all_ref_info(tool_logs=tool_logs)

	file_paths = []
	for ref_type in extra_refs_dict.keys():
		fn = REF_INFO_TO_FILE_PATH_FUNC_DICT[ref_type]
		paths = fn(extra_refs_dict[ref_type])
		file_paths.extend(paths)
	return file_paths

def get_extra_str_to_user(tool_logs: List[ToolLog]) -> str:
	r"""
	The `log_to_user` and the value of the key `references` in ToolLog will be presented to the user.
	"""
	str_list = []

	extra_refs_dict = get_all_ref_info(tool_logs=tool_logs)

	for log in tool_logs:
		if log.log_to_user is not None:
			str_list.append(log.log_to_user.strip())

	for ref_type in extra_refs_dict.keys():
		fn = REF_INFO_TO_STR_FUNC_DICT[ref_type]
		ref_str = fn(extra_refs_dict[ref_type])
		str_list.append(ref_str.strip())

	return "\n".join(str_list)

def get_all_system_logs(tool_logs: List[ToolLog]) -> str:
	tool_log_str = "TOOLS LOG:\n"
	logs = []
	for tool_log in tool_logs:
		op_description = tool_log.log_to_system[TOOL_OP_DESCRIPTION]
		if op_description is not None:
			logs.append(op_description)
	tool_log_str += "\n".join(logs)
	return tool_log_str


def create_schema_from_fn_or_method(
    name: str,
    func: Callable[..., Any],
    additional_fields: Optional[
        List[Union[Tuple[str, Type, Any], Tuple[str, Type]]]
    ] = None,
) -> Type[BaseModel]:
	"""Create schema from function."""
	fields = {}
	params = signature(func).parameters
	for param_name in params:
		if param_name in ["self", "cls"]:
			continue
		param_type = params[param_name].annotation
		param_default = params[param_name].default

		if param_type is params[param_name].empty:
			param_type = Any

		if param_default is params[param_name].empty:
			# Required field
			fields[param_name] = (param_type, FieldInfo())
		elif isinstance(param_default, FieldInfo):
			# Field with pydantic.Field as default value
			fields[param_name] = (param_type, param_default)
		else:
			fields[param_name] = (param_type, FieldInfo(default=param_default))

	additional_fields = additional_fields or []
	for field_info in additional_fields:
		if len(field_info) == 3:
			field_info = cast(Tuple[str, Type, Any], field_info)
			field_name, field_type, field_default = field_info
			fields[field_name] = (field_type, FieldInfo(default=field_default))
		elif len(field_info) == 2:
			# Required field has no default value
			field_info = cast(Tuple[str, Type], field_info)
			field_name, field_type = field_info
			fields[field_name] = (field_type, FieldInfo())
		else:
			raise ValueError(
				f"Invalid additional field info: {field_info}. "
				"Must be a tuple of length 2 or 3."
			)

	return create_model(name, **fields)  # type: ignore
