from yaml_reference.yaml import YAML

__all__ = ["YAML"]

# setattr(yaml, "load", recursively_resolve_after(yaml.load))
# setattr(yaml, "load_all", recursively_resolve_after(yaml.load_all))
# setattr(yaml, "dump", recursively_unresolve_before(yaml.dump))
# setattr(yaml, "dump_all", recursively_unresolve_before(yaml.dump_all))
