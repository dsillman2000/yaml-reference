import json
import sys
from pathlib import Path

from yaml_reference import YAMLReference


def compile_main(input_file: str):
    """
    Compile a YAML file from the given input path containing !reference tags into a JSON file with resolved references.
    The resulting output JSON document (dumped to stdout) will be "safely" formatted:

        1. Keys in mappings are sorted, and
        2. Indentation is a consistent 2 spaces.

    This is intended to accurately portray the contents of the YAML file as loaded into memory, demonstrating the
    resolution of references in deterministic way.

    Args:
        input_file (str): Path to the input YAML file with references to resolve and print as JSON.
    """
    input_path = Path(input_file)
    if not input_path.exists():
        print(f'Error: Input file "{input_path}" does not exist.', file=sys.stderr)
        sys.exit(1)

    yaml = YAMLReference(typ="safe")

    data = yaml.load(input_path.open("r"))

    json.dump(data, sys.stdout, sort_keys=True, indent=2)


def compile_cli():
    import argparse

    parser = argparse.ArgumentParser(
        description=(
            "Compile a YAML file containing !reference tags into a new YAML file with resolved references. "
            "Expects a YAML file to be provided in stdin. Outputs JSON content to stdout."
        )
    )
    parser.add_argument(
        "input_file",
        help="Path to the input YAML file with references to resolve and print as JSON.",
    )
    args = parser.parse_args()
    if not args.input_file:
        print("Error: Input file path is required.", file=sys.stderr)
        sys.exit(1)

    compile_main(args.input_file)
