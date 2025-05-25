import io
import pprint
from typing import IO, Any

from ruamel.yaml import (
    YAML,
    DocumentEndEvent,
    DocumentStartEvent,
    Event,
    MappingEndEvent,
    MappingStartEvent,
    ScalarEvent,
    SequenceEndEvent,
    SequenceStartEvent,
    StreamEndEvent,
    StreamStartEvent,
)


def load_anchor_from_file(yaml: YAML, stream: IO, anchor: str) -> Any:
    """
    Load a YAML file and return the data as a dictionary.

    Args:
        yaml (YAML): The YAML loader object.
        stream (IO): A file-like object containing the YAML data.
        anchor (str): The anchor to resolve.

    Returns:
        Any: The loaded YAML data.
    """
    if anchor is None:
        raise ValueError("Anchor cannot be None")
    level = 0
    events: list[Event] = []
    for event in yaml.parse(stream):
        if isinstance(event, ScalarEvent) and event.anchor == anchor:
            events = [event]
            break
        elif isinstance(event, MappingStartEvent) and event.anchor == anchor:
            events = [event]
            level = 1
        elif isinstance(event, SequenceStartEvent) and event.anchor == anchor:
            events = [event]
            level = 1
        elif level > 0:
            events.append(event)
            if isinstance(event, (MappingStartEvent, SequenceStartEvent)):
                level += 1
            elif isinstance(event, (MappingEndEvent, SequenceEndEvent)):
                level -= 1
            if level == 0:
                break
    if not events:
        raise ValueError(f"Anchor '{anchor}' not found in {stream.name}")
    events = [StreamStartEvent(), DocumentStartEvent()] + events + [DocumentEndEvent(), StreamEndEvent()]

    # Ensure we inherit the "stream name"
    strio = io.StringIO()
    setattr(strio, "name", stream.name)
    # Get a fresh YAML instance
    _yaml = yaml.__class__()
    _yaml.emit(events, strio)
    strio.seek(0)
    return yaml.load(strio)
