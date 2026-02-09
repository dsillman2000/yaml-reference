import os
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML


class Reference:
    """Represents a reference to another YAML file.

    This class is used as a marker for YAML references and is registered
    with ruamel.yaml to handle the `!reference` tag.

    Args:
        path (str): Relative path to the referenced YAML file. Explicitly provided by the user in the YAML document.
        location (str): Absolute path to the YAML file containing the reference. Implicitly provided by the
            YAML parser.
    """

    path: str
    location: str
    yaml_tag = "!reference"

    def __init__(self, path: str, location: str):
        self.path = path
        self.location = location

    def __repr__(self):
        return f'Reference(path="{self.path}", location="{self.location}")'


class ReferenceAll:
    """Represents a reference to multiple YAML files matching a glob pattern.

    This class is used as a marker for YAML references and is registered
    with ruamel.yaml to handle the `!reference-all` tag.

    Args:
        glob (str): Glob pattern to match multiple YAML files.
    """

    glob: str
    location: str
    yaml_tag = "!reference-all"

    def __init__(self, glob: str):
        self.glob = glob
        self.location = None  # type:ignore

    def __repr__(self):
        return f'ReferenceAll(glob="{self.glob}")'


def _check_file_path(path: str | Path | os.PathLike) -> Path:
    if not isinstance(path, Path):
        path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"File '{path}' does not exist.")
    if not path.is_file():
        raise ValueError(f"'{path}' is not a file.")
    return path


def parse_yaml_with_references(file_path: str | Path | os.PathLike) -> Any:
    """
    Interface method for reading a YAML file into memory which contains references. References are not resolved in the
    return value, but just maintained as `Reference`/`ReferenceAll` objects.

    Args:
        file_path (str | Path | os.PathLike): The path to the YAML file which contains references.

    Returns:
        Any: The parsed YAML data with references maintained as `Reference`/`ReferenceAll` objects.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the file is not a valid YAML file.

    """
    path: Path = _check_file_path(file_path)

    yaml = YAML(typ="safe")
    yaml.register_class(Reference)
    yaml.register_class(ReferenceAll)

    with path.open("r") as f:
        parsed = yaml.load(f)

    parsed = _recursively_attribute_location_to_references(parsed, path)
    return parsed


def _recursively_attribute_location_to_references(data: Any, base_path: Path):
    if isinstance(data, Reference):
        if not hasattr(data, "location"):
            data.location = str(base_path)
    elif isinstance(data, ReferenceAll):
        if not hasattr(data, "location"):
            data.location = str(base_path)
    elif isinstance(data, list):
        return [
            _recursively_attribute_location_to_references(item, base_path)
            for item in data
        ]
    elif isinstance(data, dict):
        return {
            key: _recursively_attribute_location_to_references(value, base_path)
            for key, value in data.items()
        }
    return data


def _recursively_resolve_references(data: Any) -> Any:
    if isinstance(data, Reference):
        abs_path = (Path(data.location).parent / data.path).resolve()
        parsed = parse_yaml_with_references(abs_path)
        return _recursively_resolve_references(parsed)
    elif isinstance(data, ReferenceAll):
        glob_results = Path(data.location).parent.glob(data.glob)
        abs_paths = [path.resolve() for path in glob_results]
        if not abs_paths:
            raise FileNotFoundError(
                f'No files found matching glob pattern "{data.glob}" in directory "{Path(data.location).parent}"'
            )
        abs_paths = sorted(abs_paths, key=lambda x: str(x))
        parsed = [parse_yaml_with_references(path) for path in abs_paths]
        return [_recursively_resolve_references(item) for item in parsed]
    elif isinstance(data, list):
        return [_recursively_resolve_references(item) for item in data]
    elif isinstance(data, dict):
        return {
            key: _recursively_resolve_references(value) for key, value in data.items()
        }
    else:
        return data


def load_yaml_with_references(file_path: str | Path | os.PathLike) -> Any:
    """
    Interface method for reading a YAML file into memory which contains references. References are resolved recursively
    such that the returned data is a fully resolved YAML structure without `Reference`/`ReferenceAll` objects.

    Args:
        file_path (str | Path | os.PathLike): The path to the YAML file which contains references.

    Returns:
        Any: The parsed YAML data with references recursively resolved.

    Raises:
        FileNotFoundError: If a referenced file does not exist.
        ValueError: If a referenced file is not a valid YAML file.
        ValueError: If a circular reference is detected.

    """
    path = _check_file_path(file_path)
    parsed = parse_yaml_with_references(path)
    return _recursively_resolve_references(parsed)


__all__ = ["parse_yaml_with_references", "load_yaml_with_references"]
