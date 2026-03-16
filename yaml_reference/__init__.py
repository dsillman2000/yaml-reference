import io
import os
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import IO, Any, Optional, Sequence, Union

from ruamel.yaml import YAML, events
from ruamel.yaml.tag import Tag


class Reference:
    """Represents a reference to another YAML file.

    This class is used as a marker for YAML references and is registered
    with ruamel.yaml to handle the `!reference` tag.

    Args:
        path (str): Relative path to the referenced YAML file. Explicitly provided by the user in the YAML document.
        anchor (Optional[str]): Optional anchor to extract a specific section from the referenced YAML file. Explicitly
            provided by the user in the YAML document.
        location (str): Absolute path to the YAML file containing the reference. Implicitly provided by the
            YAML parser.
    """

    path: str
    anchor: Optional[str]
    location: str
    yaml_tag = "!reference"

    def __init__(self, path: str, anchor: Optional[str] = None):
        self.path = path
        self.anchor = anchor
        if Path(self.path).is_absolute():
            raise ValueError(
                f"When supplying a path to !reference, the path must be relative. Got:\n{self.path}"
            )
        self.location = None  # type: ignore

    def __repr__(self):
        anchor_param = f', anchor="{self.anchor}"' if self.anchor is not None else ""
        return (
            f'Reference(path="{self.path}"{anchor_param}, location="{self.location}")'
        )

    @classmethod
    def from_yaml(cls, constructor, node):
        if node.id == "scalar":
            return cls(constructor.construct_scalar(node))
        mapping = constructor.construct_mapping(node)
        path = mapping["path"]
        anchor = mapping.get("anchor")
        return cls(path, anchor)


class ReferenceAll:
    """Represents a reference to multiple YAML files matching a glob pattern.

    This class is used as a marker for YAML references and is registered
    with ruamel.yaml to handle the `!reference-all` tag.

    Args:
        glob (str): Glob pattern to match multiple YAML files.
        anchor (Optional[str]): Optional anchor to extract specific sections from the matched YAML files.
        location (str): Absolute path to the YAML file containing the reference. Implicitly provided by the YAML parser.
    """

    glob: str
    anchor: Optional[str]
    location: str
    yaml_tag = "!reference-all"

    def __init__(self, glob: str, anchor: Optional[str] = None):
        self.glob = glob
        self.anchor = anchor
        # Construct a path replacing globs with a placeholder to check if glob is absolute
        _path = glob.replace("*", "abc")
        if Path(_path).is_absolute():
            raise ValueError(
                f"When supplying a glob to !reference-all, the glob must be relative. Got:\n{self.glob}"
            )
        self.location = None  # type:ignore

    def __repr__(self):
        anchor_component = (
            f', anchor="{self.anchor}"' if self.anchor is not None else ""
        )
        return f'ReferenceAll(glob="{self.glob}"{anchor_component}, location="{self.location}")'

    @classmethod
    def from_yaml(cls, constructor, node):
        if node.id == "scalar":
            return cls(constructor.construct_scalar(node))
        mapping = constructor.construct_mapping(node)
        glob = mapping["glob"]
        anchor = mapping.get("anchor")
        return cls(glob, anchor)


class Ignore:
    """Represents an ignore marker for YAML content.

    This class is used as a marker for YAML content that should be ignored and is registered
    with ruamel.yaml to handle the `!ignore` tag. Any content marked with `!ignore` will be
    parsed but effectively discarded in the final output.

    Args:
        content (Any): The YAML content associated with this tag that should be ignored.
    """

    content: Any
    yaml_tag = "!ignore"

    def __init__(self, content: Any):
        self.content = content

    def __repr__(self):
        return f"Ignore(content={repr(self.content)})"

    @classmethod
    def from_yaml(cls, constructor, node):
        # Construct the underlying content based on the node type instead of
        # calling construct_object(node), which can recurse back into this
        # method or yield partially constructed placeholders with ruamel.yaml.
        if node.id == "scalar":
            content = constructor.construct_scalar(node)
        elif node.id == "sequence":
            content = constructor.construct_sequence(node)
        elif node.id == "mapping":
            content = constructor.construct_mapping(node)
        else:
            # Fallback for any unexpected node types.
            content = constructor.construct_object(node)
        return cls(content)


class Flatten:
    """Represents a flattening operation for nested sequences.

    This class is used as a marker for YAML flattens and is registered
    with ruamel.yaml to handle the `!flatten` tag. It recursively flattens
    nested sequences while preserving non-sequence items.

    Args:
        sequence (Sequence[Any]): A sequence potentially containing nested sequences.
    """

    sequence: Sequence[Any]
    yaml_tag = "!flatten"

    def __init__(self, sequence: Sequence[Any]):
        self.sequence = sequence

    def __repr__(self):
        return f"Flatten(sequence={self.sequence})"

    def flattened(self) -> Sequence[Any]:
        """Recursively flatten this sequence.

        Processes the stored sequence, flattening all nested lists and sequences
        while recursively handling nested Flatten and Merge objects. Non-sequence
        items are preserved as-is.

        Returns:
            Sequence[Any]: The flattened sequence.
        """

        def _flatten_list(lst: list) -> list:
            """Helper method to recursively flatten a list."""
            flattened = []
            for item in lst:
                if isinstance(item, list):
                    flattened.extend(_flatten_list(item))
                else:
                    flattened.append(item)
            return flattened

        # Recursively flatten nested sequences
        result = []
        for item in self.sequence:
            if isinstance(item, Flatten):
                # Recursively flatten nested Flatten objects
                result.extend(item.flattened())
            elif isinstance(item, Merge):
                # Keep merges intact - they will be evaluated later.
                result.append(item)
            elif isinstance(item, list):
                # Recursively flatten nested lists
                result.extend(_flatten_list(item))
            else:
                result.append(item)
        return result

    @classmethod
    def from_yaml(cls, constructor, node):
        seq = constructor.construct_sequence(node)
        return cls(seq)


class Merge:
    """Represents a merge operation combining multiple YAML mappings.

    This class is used as a marker for YAML merges and is registered
    with ruamel.yaml to handle the `!merge` tag. It combines multiple
    mappings (dictionaries) into a single mapping with later mappings
    overriding keys from earlier ones.

    Args:
        sequence (Sequence[Any]): A sequence of mappings (dicts) to be merged.
                                  Later mappings override earlier ones.
    """

    sequence: Sequence[Any]
    yaml_tag = "!merge"

    def __init__(self, sequence: Sequence[Any]):
        self.sequence = sequence

    def __repr__(self):
        return f"Merge(sequence={self.sequence})"

    def merged(self) -> dict:
        """Recursively merge all mappings in this sequence.

        Flattens nested sequences first, then merges all mapping items
        sequentially. Later mappings override keys from earlier ones.
        Non-mapping items in the sequence (after flattening) raise a ValueError.

        Returns:
            dict: The merged mapping.

        Raises:
            ValueError: If the sequence contains non-mapping items after flattening.
        """
        # First, flatten the sequence to ensure all items are at the same level
        flattened_sequence = flatten_sequences(Flatten(self.sequence))
        merged_dict = {}
        for item in flattened_sequence:
            if isinstance(item, Merge):
                # Recursively merge nested Merge objects
                item |= item.merged()
            if isinstance(item, dict):
                merged_dict |= item
            else:
                raise ValueError(
                    f"All items in the sequence for !merge must be mappings. Got: {item}"
                )
        return merged_dict

    @classmethod
    def from_yaml(cls, constructor, node):
        seq = constructor.construct_sequence(node)
        return cls(seq)


@dataclass
class MultiDocument:
    documents: list[Any]
    is_multi_document: bool

    def __repr__(self):
        return (
            "MultiDocument("
            f"documents={self.documents!r}, is_multi_document={self.is_multi_document!r}"
            ")"
        )


PathLike = Union[str, Path, os.PathLike]


def _build_yaml_loader() -> YAML:
    yaml = YAML(typ="safe")
    yaml.register_class(Reference)
    yaml.register_class(ReferenceAll)
    yaml.register_class(Flatten)
    yaml.register_class(Merge)
    yaml.register_class(Ignore)
    return yaml


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


def _collect_document_event_streams(yaml: YAML, stream: IO) -> list[list[events.Event]]:
    document_streams = []
    current_document = None
    for event in yaml.parse(stream):
        if isinstance(event, events.DocumentStartEvent):
            current_document = [events.StreamStartEvent(), event]
        elif isinstance(event, events.DocumentEndEvent):
            if current_document is None:
                current_document = [
                    events.StreamStartEvent(),
                    events.DocumentStartEvent(),
                ]
            current_document.append(event)
            current_document.append(events.StreamEndEvent())
            document_streams.append(current_document)
            current_document = None
        elif not isinstance(event, (events.StreamStartEvent, events.StreamEndEvent)):
            if current_document is not None:
                current_document.append(event)
    return document_streams


def _extract_anchor_from_parser_events(
    yaml: YAML, parsed_events: Sequence[events.Event], anchor: str
) -> Any:
    anchor_lookup = dict()
    level_lookup = defaultdict(int)
    _nonzero_keys = lambda dd: [key for key, value in dd.items() if value > 0]  # noqa: E731
    for event in parsed_events:
        if (
            hasattr(event, "anchor")
            and event.anchor is not None
            and not isinstance(event, events.AliasEvent)
        ):
            anchor_str = str(event.anchor)
            anchor_lookup[anchor_str] = [event]
            if isinstance(event, (events.SequenceStartEvent, events.MappingStartEvent)):
                level_lookup[anchor_str] = 1
        if keys := _nonzero_keys(level_lookup):
            for key in keys:
                # Don't double-add an event that was just registered as a new anchor's start
                if (
                    hasattr(event, "anchor")
                    and event.anchor is not None
                    and str(event.anchor) == key
                ):
                    continue
                anchor_lookup[key] += [event]
                if isinstance(
                    event, (events.SequenceStartEvent, events.MappingStartEvent)
                ):
                    level_lookup[key] += 1
                elif isinstance(
                    event, (events.SequenceEndEvent, events.MappingEndEvent)
                ):
                    level_lookup[key] -= 1
    if anchor not in anchor_lookup:
        raise ValueError(f"Anchor '{anchor}' not found in the YAML document.")
    anchor_content = anchor_lookup[anchor]
    if not isinstance(anchor_content[0], events.DocumentStartEvent):
        anchor_content = [
            events.StreamStartEvent(),
            events.DocumentStartEvent(),
        ] + anchor_content
    if not isinstance(anchor_content[-1], events.DocumentEndEvent):
        anchor_content += [events.DocumentEndEvent(), events.StreamEndEvent()]

    # Check - do we have any unresolved aliases? Recursively resolve.
    def _resolve_aliases(my_events: list[events.Event]) -> list[events.Event]:
        resolved = []
        for event in my_events:
            if isinstance(event, events.AliasEvent):
                if event.anchor not in anchor_lookup:
                    raise ValueError(
                        f"Alias '{event.anchor}' not found in the YAML document."
                    )
                resolved += _resolve_aliases(anchor_lookup[event.anchor])
            else:
                resolved.append(event)
        return resolved

    imputed = _resolve_aliases(anchor_content)

    # Fix scalar events with no ctag set.  When a scalar is extracted from a
    # mapping-value context and re-emitted as a document root, ruamel.yaml's
    # emitter accesses `event.ctag.handle`.  If ctag is None, the emitter
    # crashes — particularly for empty-string values where it unconditionally
    # reads ctag.  We assign a proper Tag object and set implicit=(True,True)
    # so the emitter can omit the tag; yaml.load() still resolves the correct
    # type from the value and style.
    _str_tag = Tag(suffix="tag:yaml.org,2002:str")
    for event in imputed:
        if (
            isinstance(event, events.ScalarEvent)
            and getattr(event, "ctag", None) is None
        ):
            event.ctag = _str_tag
            event.implicit = (True, True)

    strio = io.StringIO()
    try:
        yaml.__class__().emit(imputed, strio)
    except Exception as e:
        msg = f"Error emitting YAML events for anchor '{anchor}': {e}"
        msg += (
            "\nEvent stream:\n[\n  "
            + ",\n  ".join(str(event) for event in imputed)
            + "\n]"
        )
        raise ValueError(msg)
    strio.seek(0)
    document = _build_yaml_loader().load(strio)
    return document


def _parse_yaml_documents(
    file_path: PathLike,
    anchor: Optional[str] = None,
    allow_paths: Sequence[PathLike] = [],
) -> MultiDocument:
    if not allow_paths:
        allow_paths = [Path(file_path).parent.absolute()]
    path: Path = _check_file_path(file_path, allow_paths=allow_paths)

    if anchor is None:
        yaml = _build_yaml_loader()
        with path.open("r") as f:
            parsed_documents = list(yaml.load_all(f))
    else:
        yaml = _build_yaml_loader()
        with path.open("r") as f:
            document_streams = _collect_document_event_streams(yaml, f)
        if not document_streams:
            raise ValueError(f"Anchor '{anchor}' not found in the YAML document.")
        parsed_documents = [
            _extract_anchor_from_parser_events(yaml, document_stream, anchor)
            for document_stream in document_streams
        ]

    if not parsed_documents:
        parsed_documents = [None]

    parsed_documents = [
        _recursively_attribute_location_to_references(document, path)
        for document in parsed_documents
    ]
    return MultiDocument(
        documents=parsed_documents,
        is_multi_document=len(parsed_documents) > 1,
    )


def parse_yaml_with_references(
    file_path: PathLike,
    anchor: Optional[str] = None,
    allow_paths: Sequence[PathLike] = [],
) -> Any:
    """
    Interface method for reading a YAML file into memory which contains references. References are not resolved in the
    return value, but just maintained as `Reference`/`ReferenceAll` objects.

    Args:
        file_path (str | Path | os.PathLike): The path to the YAML file which contains references.
        anchor (str, optional): The anchor to use for the YAML references.
        allow_paths (list[str | Path | os.PathLike]): List of paths that are allowed to be referenced.

    Returns:
        Any: The parsed YAML data with references maintained as `Reference`/`ReferenceAll` objects.

    Raises:
        FileNotFoundError: If the specified file does not exist.
        ValueError: If the file is not a valid YAML file.

    """
    parsed = _parse_yaml_documents(
        file_path,
        anchor=anchor,
        allow_paths=allow_paths,
    )
    if not parsed.is_multi_document and len(parsed.documents) == 1:
        return parsed.documents[0]
    return parsed


def _recursively_attribute_location_to_references(data: Any, base_path: Path):
    if isinstance(data, MultiDocument):
        return MultiDocument(
            documents=[
                _recursively_attribute_location_to_references(item, base_path)
                for item in data.documents
            ],
            is_multi_document=data.is_multi_document,
        )
    if isinstance(data, Flatten):
        return Flatten(
            sequence=[
                _recursively_attribute_location_to_references(item, base_path)
                for item in data.sequence
            ]
        )
    if isinstance(data, Ignore):
        return Ignore(
            content=_recursively_attribute_location_to_references(
                data.content, base_path
            )
        )
    if isinstance(data, Merge):
        return Merge(
            sequence=[
                _recursively_attribute_location_to_references(item, base_path)
                for item in data.sequence
            ]
        )
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


def _is_path_allowed(path: Path, allow_paths: Sequence[Path]) -> bool:
    """Check whether a resolved path is accessible given the allow_paths configuration.

    Unlike `_check_file_path`, this never raises; it returns `False` for paths that
    do not exist, are not regular files, or fall outside every entry in *allow_paths*.
    An empty *allow_paths* sequence means "no directory restrictions" (all existing files
    are considered allowed).

    Args:
        path: Resolved, absolute path to check.
        allow_paths: List of allowed directory paths.

    Returns:
        True if the path is an accessible file within an allowed directory (or no
        restrictions are in place). False otherwise.
    """
    if not path.exists() or not path.is_file():
        return False
    if not allow_paths:
        return True
    for allow_path in allow_paths:
        if path.is_relative_to(allow_path):
            return True
    return False


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

    if isinstance(data, MultiDocument):
        return MultiDocument(
            documents=[
                _recursively_resolve_references(
                    item, allow_paths=allow_paths, visited_paths=visited_paths
                )
                for item in data.documents
            ],
            is_multi_document=data.is_multi_document,
        )

    if isinstance(data, Flatten):
        return Flatten(
            sequence=[
                _recursively_resolve_references(
                    item, allow_paths=allow_paths, visited_paths=visited_paths
                )
                for item in data.sequence
            ]
        )

    if isinstance(data, Ignore):
        return Ignore(
            content=_recursively_resolve_references(
                data.content, allow_paths=allow_paths, visited_paths=visited_paths
            )
        )

    if isinstance(data, Merge):
        return Merge(
            sequence=[
                _recursively_resolve_references(
                    item, allow_paths=allow_paths, visited_paths=visited_paths
                )
                for item in data.sequence
            ]
        )

    if isinstance(data, Reference):
        abs_path = (Path(data.location).parent / data.path).resolve()

        # Check for circular reference and track path
        _check_and_track_path(abs_path, visited_paths)

        parsed = _parse_yaml_documents(
            abs_path, anchor=data.anchor, allow_paths=allow_paths
        )

        if len(parsed.documents) != 1:
            visited_paths.remove(abs_path)
            raise ValueError(
                f"Referenced file '{abs_path}' contains multiple YAML documents and cannot be used with !reference."
            )

        resolved = _recursively_resolve_references(
            parsed.documents[0], allow_paths=allow_paths, visited_paths=visited_paths
        )

        # Remove current path from visited set after processing
        visited_paths.remove(abs_path)

        return resolved

    elif isinstance(data, ReferenceAll):
        glob_results = Path(data.location).parent.glob(data.glob)
        abs_paths = [path.resolve() for path in glob_results]

        # Empty glob match -> silent omission, return empty list.
        if not abs_paths:
            return []

        # Precompute allowed paths sequence once to avoid repeated list()
        # construction in the comprehension below.
        allowed_paths_seq = list(allow_paths)

        # Security invariant: filter out disallowed / nonexistent paths *before*
        # opening any file.  Relative-path violations are silently omitted here;
        # absolute-path violations are caught earlier in ReferenceAll.__init__.
        abs_paths = [p for p in abs_paths if _is_path_allowed(p, allowed_paths_seq)]

        # All matched paths were disallowed → silent omission, return empty list.
        if not abs_paths:
            return []

        # Sort only the allowed paths to avoid sorting entries that will be dropped.
        abs_paths = sorted(abs_paths, key=lambda x: str(x))
        resolved_items = []
        for path in abs_paths:
            # Check for circular reference and track path
            _check_and_track_path(path, visited_paths)

            parsed = _parse_yaml_documents(
                path, anchor=data.anchor, allow_paths=allow_paths
            )
            resolved = _recursively_resolve_references(
                parsed, allow_paths=allow_paths, visited_paths=visited_paths
            )
            if isinstance(resolved, MultiDocument):
                resolved_items.extend(resolved.documents)
            else:
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


def flatten_sequences(data: Any) -> Any:
    """
    Given an object which may contain Flatten(...) objects which was parsed from a YAML document containing !flatten
    tags, return the object without any Flatten(...) objects, but having flattened all sequences marked with them.
    """
    if isinstance(data, MultiDocument):
        return MultiDocument(
            documents=[flatten_sequences(item) for item in data.documents],
            is_multi_document=data.is_multi_document,
        )
    if isinstance(data, Flatten):
        return data.flattened()
    if isinstance(data, Merge):
        # Recursively flatten sequences in Merge objects as well
        return Merge(sequence=[flatten_sequences(item) for item in data.sequence])
    if isinstance(data, list):
        return [flatten_sequences(item) for item in data]
    elif isinstance(data, dict):
        return {key: flatten_sequences(value) for key, value in data.items()}
    else:
        return data


def merge_mappings(data: Any) -> Any:
    """
    Given an object which may contain Merge(...) objects which was parsed from a YAML document containing !merge
    tags, return the object without any Merge(...) objects, but having merged all mappings marked with them.
    """
    if isinstance(data, MultiDocument):
        return MultiDocument(
            documents=[merge_mappings(item) for item in data.documents],
            is_multi_document=data.is_multi_document,
        )
    if isinstance(data, Merge):
        return merge_mappings(data.merged())
    if isinstance(data, list):
        return [merge_mappings(item) for item in data]
    elif isinstance(data, dict):
        return {key: merge_mappings(value) for key, value in data.items()}
    else:
        return data


def prune_ignores(data: Any) -> Any:
    """
    Given an object which may contain Ignore(...) objects which was parsed from a YAML document containing !ignore
    tags, return the object with all Ignore(...) objects removed. If an Ignore(...) object is found in a list, it is
    removed from the list. If an Ignore(...) object is found as a value in a dict, the key-value pair is removed from
    the dict. If an Ignore(...) object is found as a value which is not in a list or dict, it is replaced with None.
    """
    if isinstance(data, MultiDocument):
        if not data.is_multi_document:
            if not data.documents:
                return MultiDocument(documents=[None], is_multi_document=False)
            return MultiDocument(
                documents=[prune_ignores(data.documents[0])],
                is_multi_document=False,
            )

        pruned_documents = []
        for item in data.documents:
            if isinstance(item, Ignore):
                continue
            pruned_item = prune_ignores(item)
            if pruned_item is not None:
                pruned_documents.append(pruned_item)
        return MultiDocument(documents=pruned_documents, is_multi_document=True)
    if isinstance(data, Ignore):
        return None
    if isinstance(data, Flatten):
        return Flatten(
            sequence=[
                prune_ignores(item)
                for item in data.sequence
                if not isinstance(item, Ignore)
            ]
        )
    if isinstance(data, Merge):
        return Merge(
            sequence=[
                prune_ignores(item)
                for item in data.sequence
                if not isinstance(item, Ignore)
            ]
        )
    if isinstance(data, list):
        return [prune_ignores(item) for item in data if not isinstance(item, Ignore)]
    elif isinstance(data, dict):
        return {
            key: prune_ignores(value)
            for key, value in data.items()
            if not isinstance(value, Ignore)
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
    parsed = _parse_yaml_documents(path, allow_paths=allow_paths)

    # Initialize visited paths with the root file to detect self-references
    visited_paths = {path.resolve()}

    resolved = _recursively_resolve_references(
        parsed,
        allow_paths=allow_paths,  # type: ignore
        visited_paths=visited_paths,
    )
    # Prune ignores after full resolution so that Ignore wrappers introduced by
    # referenced files propagate up to their parent containers, allowing keys and
    # list items whose resolved value is !ignore to be dropped entirely rather
    # than replaced with null.
    pruned = prune_ignores(resolved)
    flattened = flatten_sequences(pruned)
    merged = merge_mappings(flattened)
    if isinstance(merged, MultiDocument):
        if merged.is_multi_document:
            return merged.documents
        if not merged.documents:
            return None
        if len(merged.documents) == 1:
            return merged.documents[0]
        return None
    return merged


__all__ = [
    "parse_yaml_with_references",
    "load_yaml_with_references",
    "flatten_sequences",
    "Flatten",
    "merge_mappings",
    "Merge",
    "MultiDocument",
    "prune_ignores",
    "Ignore",
]
