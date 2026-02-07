import sys
from pathlib import Path
from typing import Optional

from ruamel.yaml import YAML as YAMLRuamel

from yaml_reference import YAMLReference


def compile_main(
    input_file: Optional[str] = None,
    output_file: Optional[str] = None,
):
    """
    Compile a YAML file containing !reference tags into a new YAML file with resolved references. The resulting output
    YAML document will be "safely" formatted:

        1. Aliases / anchors are resolved,
        2. All data is block-formatted, and
        3. Keys of mappings are sorted.

    This is intended to accurately portray the contents of the YAML file as loaded into memory, demonstrating the
    resolution of references in deterministic way.

    Args:
        input_file (str): The path to the input YAML file. If not provided, the function will read from standard input.
        output_file (str): The path to the output YAML file. If not provided, the function will write to standard output.
    """
    yaml = YAMLReference(typ="safe")

    if input_file is None:
        input_handle = sys.stdin
    else:
        input_handle = Path(input_file).open("r")

    if output_file is None:
        output_handle = sys.stdout
    else:
        output_handle = Path(output_file).open("w")

    data = yaml.load(input_handle)
    writer_yaml = YAMLRuamel(typ="safe")
    writer_yaml.representer.ignore_aliases = lambda *_: True
    writer_yaml.representer.default_flow_style = False

    writer_yaml.dump(data, output_handle)


def compile_cli():
    import argparse

    parser = argparse.ArgumentParser(
        description="Compile a YAML file containing !reference tags into a new YAML file with resolved references."
    )
    parser.add_argument(
        "-i",
        "--input",
        type=str,
        help="Path to the input YAML file. If not provided, reads from stdin.",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=str,
        help="Path to the output YAML file. If not provided, writes to stdout.",
    )
    args = parser.parse_args()
    compile_main(args.input, args.output)
