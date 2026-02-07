from typing import Callable

from ruamel.yaml import YAML as _YAML

from yaml_reference.reference import (
    Reference,
    ReferenceAll,
    recursively_resolve_after,
)


def _attach_stream_name_to_constructor(yaml, func: Callable) -> Callable:
    def wrapper(*args, **kwargs):
        stream = args[0] if args else kwargs.get("stream")
        if stream is None or not hasattr(stream, "name"):
            raise ValueError(f"Stream {stream} must have a name attribute")
        yaml.constructor.stream_name = stream.name
        yaml.Constructor.stream_name = stream.name
        rval = func(*args, **kwargs)
        yaml.constructor.stream_name = None
        yaml.Constructor.stream_name = None
        return rval

    return wrapper


class YAML(_YAML):
    """
    A class to represent a YAML object with custom loading and dumping behavior.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.constructor.add_constructor("!reference", Reference.from_yaml)
        self.constructor.add_constructor("!reference-all", ReferenceAll.from_yaml)
        # I'm not sure which of these I should use, so I'll attach the state to both.
        setattr(self.constructor, "stream_name", None)
        setattr(self.Constructor, "stream_name", None)
        self.load = _attach_stream_name_to_constructor(self, recursively_resolve_after(self, self.load))
        self.load_all = _attach_stream_name_to_constructor(self, recursively_resolve_after(self, self.load_all))
        # self.representer.add_representer(Reference, Reference.to_yaml)
        # self.representer.add_representer(ReferenceAll, ReferenceAll.to_yaml)
        # self.dump = recursively_unresolve_before(self.dump)
        # self.dump_all = recursively_unresolve_before(self.dump_all)


__all__ = ["YAML"]
