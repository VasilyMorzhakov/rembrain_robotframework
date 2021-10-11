import yaml


def get_config(config_file: str) -> dict:
    with open(config_file) as file:
        return yaml.load(file, Loader=yaml.BaseLoader)
