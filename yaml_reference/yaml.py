from ruamel.yaml import YAML as _YAML
from ruamel.yaml.reader import Reader

from yaml_reference.reference import (
    Reference,
    ReferenceAll,
    recursively_resolve_after,
    recursively_unresolve_before,
)


class YAML(_YAML):
    """
    A class to represent a YAML object with custom loading and dumping behavior.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.constructor.add_constructor("!reference", Reference.from_yaml)
        self.constructor.add_constructor("!reference-all", ReferenceAll.from_yaml)
        # self.representer.add_representer(Reference, Reference.to_yaml)
        # self.representer.add_representer(ReferenceAll, ReferenceAll.to_yaml)
        self.load = recursively_resolve_after(self, self.load)
        self.load_all = recursively_resolve_after(self, self.load_all)
        # self.dump = recursively_unresolve_before(self.dump)
        # self.dump_all = recursively_unresolve_before(self.dump_all)


__all__ = ["YAML"]
