import os
import inspect
import yaml


def load_config(test_obj, test_func, cfg_dir="cfg") -> dict:
    """
    Loads and returns config from the path
    `./cfg/config_{test_func}.yaml`
    relative to the test_class file
    """
    class_dir = os.path.dirname(inspect.getfile(test_obj.__class__))
    cfg_path = os.path.join(class_dir, cfg_dir, f"config_{test_func}.yaml")
    with open(cfg_path) as f:
        return yaml.load(f, Loader=yaml.BaseLoader)


def generate_process_dict(cfg: dict, process_map: dict) -> dict:
    return {p: {"process_class": process_map[p]} for p in cfg["processes"]}
