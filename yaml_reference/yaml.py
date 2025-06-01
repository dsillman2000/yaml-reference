from typing import IO, Callable

from ruamel.yaml import YAML as _YAML
from ruamel.yaml import Constructor, RoundTripConstructor

from yaml_reference.reference import Reference, ReferenceAll, recursively_resolve


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
        # self.representer.add_representer(Reference, Reference.to_yaml)
        # self.representer.add_representer(ReferenceAll, ReferenceAll.to_yaml)
        # self.dump = recursively_unresolve_before(self.dump)
        # self.dump_all = recursively_unresolve_before(self.dump_all)

    def load(self, stream: IO, *args, **kwargs):
        """
        Load a YAML document from a stream. Internally stores the stream name for referenced filename resolution.
        """
        self.constructor.stream_name = stream.name
        self.Constructor.stream_name = stream.name
        load_result = _YAML.load(self, stream, *args, **kwargs)
        resolved_result = recursively_resolve(self, load_result)
        self.constructor.stream_name = None
        self.Constructor.stream_name = None
        return resolved_result

    def load_all(self, stream: IO, *args, **kwargs):
        """
        Load all YAML documents from a stream. Internally stores the stream name for referenced filename resolution.
        """
        self.constructor.stream_name = stream.name
        self.Constructor.stream_name = stream.name
        load_all_result = _YAML.load_all(self, stream, *args, **kwargs)
        resolved_result = [recursively_resolve(self, doc) for doc in load_all_result]
        self.constructor.stream_name = None
        self.Constructor.stream_name = None
        return resolved_result


__all__ = ["YAML"]
