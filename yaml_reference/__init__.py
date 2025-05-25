from yaml_reference.reference import Reference, recursively_resolve_after
from yaml_reference.yaml import yaml

__all__ = ["yaml"]

setattr(yaml, "load", recursively_resolve_after(yaml.load))
setattr(yaml, "load_all", recursively_resolve_after(yaml.load_all))
