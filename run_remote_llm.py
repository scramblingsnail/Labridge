import yaml
from labridge.models.remote.remote_server import run_remote_model


if __name__ == "__main__":
	cfg_path = "./model_cfg.yaml"

	with open(cfg_path, 'r') as f:
		config = yaml.safe_load(f)

	host = config["remote_host"]
	port = config["remote_port"]
	run_remote_model(host=host, port=port)
