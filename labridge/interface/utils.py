from pathlib import Path
from labridge.agent.chat_msg.msg_types import USER_TMP_DIR
from labridge.common.utils.time import get_time

import fsspec
import base64
from typing import Optional


def save_temporary_file(
	tmp_path: str,
	file_bytes: bytes,
):
	fs = fsspec.filesystem("file")
	tmp_dir = str(Path(tmp_path).parent)
	if not fs.exists(tmp_dir):
		fs.mkdirs(tmp_dir)

	with open(tmp_path, "wb") as tmp_f:
		tmp_f.write(file_bytes)

# def save_temporary_file_base64(
# 	file_base64: str,
# 	save_path: str,
# ):
# 	file_bytes = base64.b64decode(file_base64)
# 	with open(save_path, 'wb') as f:
# 		f.write(file_bytes)


def read_server_file(
	file_path: str,
) -> Optional[bytes]:
	fs = fsspec.filesystem("file")
	if not fs.exists(file_path):
		return None

	with open(file_path, "rb") as f:
		f_data = f.read()
		return f_data


# def read_server_file_base64(
# 	file_path: str,
# ) -> Optional[str]:
# 	fs = fsspec.filesystem("file")
# 	if not fs.exists(file_path):
# 		return None
#
# 	with open(file_path, "rb") as f:
# 		f_data = f.read()
# 		f_text = str(base64.b64encode(f_data), 'utf-8')
# 		return f_text
