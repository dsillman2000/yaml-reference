from yaml_reference import (
    Ignore,
    load_yaml_with_references,
    parse_yaml_with_references,
    prune_ignores,
)


def test_ignore_parse_produces_ignore_object(stage_files):
    """Test that !ignore tags are parsed into Ignore objects by parse_yaml_with_references."""
    files = {
        "test.yml": "key: !ignore some_value",
    }
    stg = stage_files(files)
    data = parse_yaml_with_references(stg / "test.yml")
    assert isinstance(data["key"], Ignore)


def test_ignore_dict_value_removed(stage_files):
    """Test that a dict value tagged with !ignore is removed from the output."""
    files = {
        "test.yml": """\
keep: hello
drop: !ignore world
""",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert "keep" in data
    assert data["keep"] == "hello"
    assert "drop" not in data


def test_ignore_list_item_removed(stage_files):
    """Test that a list item tagged with !ignore is removed from the output."""
    files = {
        "test.yml": """\
items:
  - one
  - !ignore two
  - three
""",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["items"] == ["one", "three"]


def test_ignore_standalone_value_becomes_none(stage_files):
    """Test that a standalone (non-list, non-dict) !ignore value is replaced with None."""
    files = {
        "test.yml": "!ignore standalone",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data is None


def test_ignore_multiple_items_in_list(stage_files):
    """Test that multiple !ignore items in a list are all removed."""
    files = {
        "test.yml": """\
items:
  - !ignore a
  - b
  - !ignore c
  - d
""",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["items"] == ["b", "d"]


def test_ignore_multiple_keys_in_dict(stage_files):
    """Test that multiple !ignore values in a dict are all removed."""
    files = {
        "test.yml": """\
a: !ignore 1
b: 2
c: !ignore 3
d: 4
""",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data == {"b": 2, "d": 4}


def test_ignore_mapping_value(stage_files):
    """Test that a mapping tagged with !ignore is removed."""
    files = {
        "test.yml": """\
keep:
  x: 1
drop: !ignore
  y: 2
  z: 3
""",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert "keep" in data
    assert "drop" not in data


def test_ignore_sequence_value(stage_files):
    """Test that a sequence tagged with !ignore is removed when used as a dict value."""
    files = {
        "test.yml": """\
keep: [1, 2]
drop: !ignore [3, 4]
""",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data == {"keep": [1, 2]}


def test_ignore_does_not_affect_non_tagged_content(stage_files):
    """Test that !ignore only affects tagged content and leaves everything else intact."""
    files = {
        "test.yml": """\
name: yaml-reference
version: 1.0
description: !ignore internal note
tags:
  - alpha
  - !ignore beta
  - gamma
""",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["name"] == "yaml-reference"
    assert data["version"] == 1.0
    assert "description" not in data
    assert data["tags"] == ["alpha", "gamma"]


def test_ignore_in_referenced_file(stage_files):
    """Test that !ignore tags in a referenced file are pruned during resolution."""
    files = {
        "root.yml": "contents: !reference { path: ./inner.yml }",
        "inner.yml": """\
public: visible
private: !ignore hidden
""",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "root.yml")
    assert data["contents"] == {"public": "visible"}
    assert "private" not in data["contents"]


def test_prune_ignores_standalone(stage_files):
    """Test prune_ignores() directly on a structure containing Ignore objects."""
    data = {
        "a": Ignore("should be removed"),
        "b": 42,
        "c": [1, Ignore("also removed"), 3],
    }
    result = prune_ignores(data)
    assert "a" not in result
    assert result["b"] == 42
    assert result["c"] == [1, 3]


def test_ignore_preserves_none_values(stage_files):
    """Test that existing null/None values in YAML are preserved (not confused with ignored values)."""
    files = {
        "test.yml": """\
present: ~
also_present: null
dropped: !ignore something
""",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert "present" in data
    assert data["present"] is None
    assert "also_present" in data
    assert data["also_present"] is None
    assert "dropped" not in data
