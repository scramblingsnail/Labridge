import aiohttp


async def adownload_file(url: str, save_path: str) -> str:
	r"""
	Asynchronously download file.

	Args:
		url (str): The url of the file.
		save_path (str): The save path of the file.

	Returns:
		save_path (str): The save path.
	"""
	async with aiohttp.ClientSession() as session:
		async with session.get(url) as response:
			with open(save_path, 'wb') as f:
				while True:
					chunk = await response.content.read(1024)
					if not chunk:
						break
					f.write(chunk)
	return save_path


