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
)


def pack_tool_output(tool_output: str, tool_log: str = None):
	tool_out_dict = {
		"tool_output": tool_output,
		"tool_log": tool_log,
	}
	tool_out_str = json.dumps(tool_out_dict)
	return tool_out_str


def unpack_tool_output(tool_out_json: str) -> Tuple[str, Any]:
	tool_out_dict = json.loads(tool_out_json)
	tool_output, tool_log = tool_out_dict["tool_output"], tool_out_dict["tool_log"]
	tool_log = json.loads(tool_log)
	return tool_output, tool_log


def create_schema_from_class_method(
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
