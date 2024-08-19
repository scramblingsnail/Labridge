import aiohttp
import asyncio
import os


async def adownload_file(url, save_path):
	async with aiohttp.ClientSession() as session:
		async with session.get(url) as response:
			with open(save_path, 'wb') as f:
				while True:
					chunk = await response.content.read(1024)
					if not chunk:
						break
					f.write(chunk)
	return save_path


