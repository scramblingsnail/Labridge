from pathlib import Path
from labridge.interface.types import UPLOAD_FILE_TMP_DIR
from labridge.common.utils.time import get_time

import fsspec
from typing import Optional


def save_temporary_file(
	user_id: str,
	file_name: str,
	file_bytes: bytes,
):
	root = Path(__file__)
	for i in range(3):
		root = root.parent

	fs = fsspec.filesystem("file")
	date, _ = get_time()
	tmp_dir = root / f"{UPLOAD_FILE_TMP_DIR}/{user_id}/{date}"
	if not fs.exists(tmp_dir):
		fs.mkdirs(tmp_dir)

	tmp_path = str(tmp_dir / file_name)
	with open(tmp_path, "wb") as tmp_f:
		tmp_f.write(file_bytes)
	return tmp_path


def read_server_file(
	file_path: str,
) -> Optional[bytes]:
	fs = fsspec.filesystem("file")
	if not fs.exists(file_path):
		return None

	with open(file_path, "rb") as f:
		f_data = f.read()
		return f_data




