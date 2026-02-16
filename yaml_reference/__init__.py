import os
from pathlib import Path
from typing import Any, Optional, Sequence, Union

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

    def __init__(self, path: str):
        self.path = path
        if Path(self.path).is_absolute():
            raise ValueError(
                f"When supplying a path to !reference, the path must be relative. Got:\n{self.path}"
            )
        self.location = None  # type: ignore

    def __repr__(self):
        return f'Reference(path="{self.path}", location="{self.location}")'

    @classmethod
    def from_yaml(cls, constructor, node):
        mapping = constructor.construct_mapping(node)
        path = mapping["path"]
        return cls(path)


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
        # Construct a path replacing globs with a placeholder to check if glob is absolute
        _path = glob.replace("*", "abc")
        if Path(_path).is_absolute():
            raise ValueError(
                f"When supplying a glob to !reference-all, the glob must be relative. Got:\n{self.glob}"
            )
        self.location = None  # type:ignore

    def __repr__(self):
        return f'ReferenceAll(glob="{self.glob}", location="{self.location}")'

    @classmethod
    def from_yaml(cls, constructor, node):
        mapping = constructor.construct_mapping(node)
        glob = mapping["glob"]
        return cls(glob)


PathLike = Union[str, Path, os.PathLike]


def _check_file_path(path: PathLike, allow_paths: Sequence[PathLike]) -> Path:
    if not isinstance(path, Path):
        path = Path(path)
    path = path.resolve()
    if not path.exists():
        raise FileNotFoundError(f"File '{path}' does not exist.")
    if not path.is_file():
        raise ValueError(f"'{path}' is not a file.")
    if not allow_paths:
        return path
    for allow_path in allow_paths:
        if not isinstance(allow_path, Path):
            allow_path = Path(allow_path)
        if path.is_relative_to(allow_path):
            return path
    raise PermissionError(f"File '{path}' is not allowed.")


def parse_yaml_with_references(
    file_path: PathLike, allow_paths: Sequence[PathLike] = []
) -> Any:
    """
    Interface method for reading a YAML file into memory which contains references. References are not resolved in the
    return value, but just maintained as `Reference`/`ReferenceAll` objects.

    Args:
        file_path (str | Path | os.PathLike): The path to the YAML file which contains references.
        allow_paths (list[str | Path | os.PathLike]): List of paths that are allowed to be referenced.

    Returns:
        Any: The parsed YAML data with references maintained as `Reference`/`ReferenceAll` objects.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the file is not a valid YAML file.

    """
    if not allow_paths:
        allow_paths = [Path(file_path).parent.absolute()]
    path: Path = _check_file_path(file_path, allow_paths=allow_paths)

    yaml = YAML(typ="safe")
    yaml.register_class(Reference)
    yaml.register_class(ReferenceAll)

    with path.open("r") as f:
        parsed = yaml.load(f)

    parsed = _recursively_attribute_location_to_references(parsed, path)
    return parsed


def _recursively_attribute_location_to_references(data: Any, base_path: Path):
    if isinstance(data, Reference):
        if data.location is None:
            data.location = str(base_path)
    elif isinstance(data, ReferenceAll):
        if data.location is None:
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


def _check_and_track_path(path: Path, visited_paths: set[Path]) -> None:
    """
    Check for circular reference and add path to visited set.

    Args:
        path: The file path to check and track.
        visited_paths: Set of visited file paths.

    Raises:
        ValueError: If a circular reference is detected.
    """
    if path in visited_paths:
        raise ValueError(
            f"Circular reference detected: {path} has already been visited. "
            f"Visited path chain: {visited_paths}"
        )
    visited_paths.add(path)


def _recursively_resolve_references(
    data: Any, allow_paths: Sequence[Path], visited_paths: Optional[set[Path]] = None
) -> Any:
    """
    Recursively resolve references in YAML data.

    Args:
        data: The YAML data to resolve references in.
        allow_paths: List of allowed paths for file access.
        visited_paths: Set of file paths that have been visited during resolution.
                      Used to detect circular references.

    Returns:
        The resolved YAML data with all references expanded.

    Raises:
        ValueError: If a circular reference is detected.
    """
    if visited_paths is None:
        visited_paths = set()

    if isinstance(data, Reference):
        abs_path = (Path(data.location).parent / data.path).resolve()

        # Check for circular reference and track path
        _check_and_track_path(abs_path, visited_paths)

        parsed = parse_yaml_with_references(abs_path, allow_paths=allow_paths)
        resolved = _recursively_resolve_references(
            parsed, allow_paths=allow_paths, visited_paths=visited_paths
        )

        # Remove current path from visited set after processing
        visited_paths.remove(abs_path)

        return resolved

    elif isinstance(data, ReferenceAll):
        glob_results = Path(data.location).parent.glob(data.glob)
        abs_paths = [path.resolve() for path in glob_results]
        if not abs_paths:
            raise FileNotFoundError(
                f'No files found matching glob pattern "{data.glob}" in directory "{Path(data.location).parent}"'
            )
        abs_paths = sorted(abs_paths, key=lambda x: str(x))

        resolved_items = []
        for path in abs_paths:
            # Check for circular reference and track path
            _check_and_track_path(path, visited_paths)

            parsed = parse_yaml_with_references(path, allow_paths=allow_paths)
            resolved = _recursively_resolve_references(
                parsed, allow_paths=allow_paths, visited_paths=visited_paths
            )
            resolved_items.append(resolved)

            # Remove current path from visited set after processing
            visited_paths.remove(path)

        return resolved_items

    elif isinstance(data, list):
        return [
            _recursively_resolve_references(
                item, allow_paths=allow_paths, visited_paths=visited_paths
            )
            for item in data
        ]
    elif isinstance(data, dict):
        return {
            key: _recursively_resolve_references(
                value, allow_paths=allow_paths, visited_paths=visited_paths
            )
            for key, value in data.items()
        }
    else:
        return data


def load_yaml_with_references(
    file_path: PathLike, allow_paths: Sequence[PathLike] = []
) -> Any:
    """
    Interface method for reading a YAML file into memory which contains references. References are resolved recursively
    such that the returned data is a fully resolved YAML structure without `Reference`/`ReferenceAll` objects.

    Args:
        file_path (str | Path | os.PathLike): The path to the YAML file which contains references.
        allow_paths (list[str | Path | os.PathLike]): List of paths to allow references from.

    Returns:
        Any: The parsed YAML data with references recursively resolved.

    Raises:
        FileNotFoundError: If a referenced file does not exist.
        PermissionError: If a referenced file is not readable or not in an allowed path.
        ValueError: If a referenced file is not a valid YAML file.
        ValueError: If a circular reference is detected.

    """
    if allow_paths:
        allow_paths = [Path(path).absolute() for path in allow_paths]
    else:
        allow_paths = []
    allow_paths += [Path(file_path).parent.absolute()]
    path = _check_file_path(file_path, allow_paths=allow_paths)
    parsed = parse_yaml_with_references(path, allow_paths=allow_paths)

    # Initialize visited paths with the root file to detect self-references
    visited_paths = {path.resolve()}

    return _recursively_resolve_references(
        parsed,
        allow_paths=allow_paths,  # type: ignore
        visited_paths=visited_paths,
    )


__all__ = ["parse_yaml_with_references", "load_yaml_with_references"]
