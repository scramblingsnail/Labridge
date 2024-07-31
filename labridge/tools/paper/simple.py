from llama_index.core.tools import FunctionTool
from inspect import signature

from ..base import FunctionBaseTool


def add(a: float, b: float) -> float:
	r"""
	This function is used to calculate the adding result of two float numbers: a, b

	Args:
		a (float): the first number.
		b (float): the second number.

	Returns:
		The adding result of the input `a` and `b`, that is: `a + b`
	"""
	return a + b


def multiply(a: float, b: float) -> float:
	r"""
	This function is used to calculate the multiplication result of two float numbers: a, b

	Args:
		a (float): the first number.
		b (float): the second number.

	Returns:
		The multiplication result of the input `a` and `b`, that is `a * b`
	"""
	return a * b


class AddNumberTool(FunctionBaseTool):
	def __init__(self):
		super().__init__(fn=add)

	def log(self):
		return None

class MultiplyNumberTool(FunctionBaseTool):
	def __init__(self):
		super().__init__(fn=multiply)

	def log(self):
		return None


if __name__ == "__main__":
	add_tool = FunctionTool.from_defaults(fn=add)
	mul_tool = FunctionTool.from_defaults(fn=multiply)

	print(">>> Add tool: \n")
	print(add_tool.metadata.description)

	print(">>> Multiply tool: \n")
	print(mul_tool.metadata.fn_schema.schema())

	params = signature(add).parameters
	for param_name in params:
		param_type = params[param_name].annotation
		param_default = params[param_name].default
		print(f">>> param type: {param_type}; param_default: {param_default}")

