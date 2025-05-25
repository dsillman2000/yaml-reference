def compile_main(
    input_file: str = None,
    output_file: str = None,
):
    """
    Compile a YAML file containing !reference tags into a new YAML file with resolved references.

    Args:
        input_file (str): The path to the input YAML file. If not provided, the function will read from standard input.
        output_file (str): The path to the output YAML file. If not provided, the function will write to standard output.
    """
    import sys
    from pathlib import Path

    from yaml_reference import YAML

    yaml = YAML()

    if input_file is None:
        input_file = sys.stdin.read()
        input_file = Path(input_file)
    else:
        input_file = Path(input_file)

    if output_file is None:
        output_file = sys.stdout
    else:
        output_file = Path(output_file)

    data = yaml.load(input_file)
    yaml.dump(data, output_file)


def compile_cli():
    import argparse

    parser = argparse.ArgumentParser(
        description="Compile a YAML file containing !reference tags into a new YAML file with resolved references."
    )
    parser.add_argument(
        "-i", "--input", type=str, help="Path to the input YAML file. If not provided, reads from stdin."
    )
    parser.add_argument(
        "-o", "--output", type=str, help="Path to the output YAML file. If not provided, writes to stdout."
    )
    args = parser.parse_args()
    compile_main(args.input, args.output)
