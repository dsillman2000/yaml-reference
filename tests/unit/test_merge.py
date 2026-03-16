from yaml_reference import Merge, load_yaml_with_references, parse_yaml_with_references

# Tests demonstrating parsing behavior with Merge objects


def test_parse_merge_basic(stage_files):
    """Test that parsing YAML with !merge tag creates Merge objects."""
    files = {
        "test.yml": "myMap: !merge [{a: 1}, {b: 2}]",
    }
    stg = stage_files(files)
    data = parse_yaml_with_references(stg / "test.yml")

    # Verify the parsed structure contains a Merge object, not a merged dictionary
    assert isinstance(data["myMap"], Merge)
    assert data["myMap"].sequence == [{"a": 1}, {"b": 2}]


def test_parse_merge_nested(stage_files):
    """Test that parsing YAML with nested !merge tags creates nested Merge objects."""
    files = {
        "test.yml": """
result: !merge
  - a: 1
    inner: !merge
      - {x: 1, y: 1}
      - {x: 2}
  - {b: 2}""",
    }
    stg = stage_files(files)
    data = parse_yaml_with_references(stg / "test.yml")

    # Verify the outer Merge object
    assert isinstance(data["result"], Merge)
    assert len(data["result"].sequence) == 2

    # Verify the first item in the sequence has a nested Merge object
    first_item = data["result"].sequence[0]
    assert isinstance(first_item, dict)
    assert first_item["a"] == 1
    assert isinstance(first_item["inner"], Merge)
    assert first_item["inner"].sequence == [{"x": 1, "y": 1}, {"x": 2}]

    # Verify the second item is a plain dict
    second_item = data["result"].sequence[1]
    assert isinstance(second_item, dict)
    assert second_item == {"b": 2}


def test_parse_merge_multiple_levels(stage_files):
    """Test parsing YAML with multiple levels of nested Merge objects."""
    files = {
        "test.yml": """
data: !merge
  - outer: !merge
      - inner: !merge
          - {x: 1}
          - {y: 2}
      - {z: 3}
  - {w: 4}""",
    }
    stg = stage_files(files)
    data = parse_yaml_with_references(stg / "test.yml")

    # Verify the structure preserves Merge objects at each level
    assert isinstance(data["data"], Merge)
    outer_merge = data["data"].sequence[0]["outer"]
    assert isinstance(outer_merge, Merge)
    inner_merge = outer_merge.sequence[0]["inner"]
    assert isinstance(inner_merge, Merge)
    assert inner_merge.sequence == [{"x": 1}, {"y": 2}]


def test_parse_merge_single_mapping(stage_files):
    """Test parsing YAML with !merge containing a single mapping."""
    files = {
        "test.yml": "result: !merge [{a: 1, b: 2}]",
    }
    stg = stage_files(files)
    data = parse_yaml_with_references(stg / "test.yml")

    assert isinstance(data["result"], Merge)
    assert data["result"].sequence == [{"a": 1, "b": 2}]


def test_parse_merge_empty_sequence(stage_files):
    """Test parsing YAML with !merge containing an empty sequence."""
    files = {
        "test.yml": "result: !merge []",
    }
    stg = stage_files(files)
    data = parse_yaml_with_references(stg / "test.yml")

    assert isinstance(data["result"], Merge)
    assert data["result"].sequence == []


# Evaluation of merges


def test_merge_basic(stage_files):
    """Test basic merging of nested mappings."""
    files = {
        "test.yml": "myMap: !merge [{a: 1}, {b: 2}]",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["myMap"] == {"a": 1, "b": 2}


def test_merge_nested(stage_files):
    """Test merging of nested mappings."""
    files = {
        "test.yml": """
result: !merge
  - a: 1
    inner: !merge
      - {x: 1, y: 1}
      - {x: 2}
  - {b: 2}""",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["result"] == {"a": 1, "b": 2, "inner": {"x": 2, "y": 1}}


def test_merge_ignores_ignored_sequence_items(stage_files):
    """Test that !ignore items inside a !merge sequence are omitted before merging."""
    files = {
        "test.yml": """
result: !merge
  - {a: 1}
  - !ignore {ignored: true}
  - {b: 2}
""",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["result"] == {"a": 1, "b": 2}


def test_flatten_and_merge(stage_files):
    """Test flattening and merging together."""

    # Merge some flattens
    files = {
        "test.yml": """result: !merge
  - a: 1
    inner: !merge
      - !flatten [[{x: 1}, {y: 1}], [{x: 2}]]
      - !flatten [[[{x: 3}]]]
  - {b: 2}""",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["result"] == {"a": 1, "b": 2, "inner": {"x": 3, "y": 1}}

    # Flatten some merges
    files = {
        "test.yml": """result: !flatten
  - !merge
    - a: 1
    - a: 2
  - !merge
    - - b: 1
      - b: 2
    - c: 3""",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["result"] == [{"a": 2}, {"b": 2, "c": 3}]
