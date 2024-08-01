import json


def pack_tool_output(tool_output: str, tool_log: str = None):
	tool_out_dict = {
		"tool_output": tool_output,
		"tool_log": tool_log,
	}
	tool_out_str = json.dumps(tool_out_dict)
	return tool_out_str

def unpack_tool_output(tool_out_json: str):
	tool_out_dict = json.loads(tool_out_json)
	tool_output, tool_log = tool_out_dict["tool_output"], tool_out_dict["tool_log"]
	return tool_output, tool_log
