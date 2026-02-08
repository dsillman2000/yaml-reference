import json
import sys

from yaml_reference import YAMLReference


def compile_main():
    """
    Compile a YAML file from stdin containing !reference tags into a JSON file with resolved references. The resulting
    output JSON document (dumped to stdout) will be "safely" formatted:

        1. Keys in mappings are sorted, and
        2. Indentation is a consistent 2 spaces.

    This is intended to accurately portray the contents of the YAML file as loaded into memory, demonstrating the
    resolution of references in deterministic way.
    """
    yaml = YAMLReference(typ="safe")

    data = yaml.load(sys.stdin)

    json.dump(data, sys.stdout, sort_keys=True, indent=2)


def compile_cli():
    import argparse

    argparse.ArgumentParser(
        description=(
            "Compile a YAML file containing !reference tags into a new YAML file with resolved references. "
            "Expects a YAML file to be provided in stdin. Outputs JSON content to stdout."
        )
    ).parse_args()
    compile_main()
