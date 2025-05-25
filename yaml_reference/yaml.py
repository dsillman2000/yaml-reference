from ruamel.yaml import YAML
from ruamel.yaml.reader import Reader

yaml = YAML(typ="safe")
yaml.Reader = Reader

__all__ = ["yaml"]
