import argparse
import sys
from labridge.interface.http_server import run_http_server


if __name__ == "__main__":
	print(sys.path)
	parser = argparse.ArgumentParser()
	parser.add_argument("--host", help="服务器URL", required=True)
	parser.add_argument("--port", help="服务器端口号", required=True)
	args = parser.parse_args()

	host = args.host
	port = int(args.port)

	run_http_server(host_url=host, port=port)
