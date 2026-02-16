from yaml_reference import (
    Flatten,
    flatten_sequences,
    load_yaml_with_references,
    parse_yaml_with_references,
)


def test_flatten_basic(stage_files):
    """Test basic flattening of nested sequences."""
    files = {
        "test.yml": "mySeq: !flatten [[1, 2], [3]]",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["mySeq"] == [1, 2, 3]


def test_flatten_multiple_levels(stage_files):
    """Test flattening of deeply nested sequences."""
    files = {
        "test.yml": "data: !flatten [[1, [2, 3]], [[4, 5], 6]]",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["data"] == [1, 2, 3, 4, 5, 6]


def test_flatten_empty_sequences(stage_files):
    """Test flattening with empty sequences."""
    files = {
        "test.yml": "data: !flatten [[], [1, 2], [], [3], []]",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["data"] == [1, 2, 3]


def test_flatten_single_sequence(stage_files):
    """Test flattening a single sequence (should return the flattened sequence)."""
    files = {
        "test.yml": "data: !flatten [[1, 2, 3]]",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["data"] == [1, 2, 3]


def test_flatten_nested_flatten_tags(stage_files):
    """Test flattening with nested !flatten tags."""
    files = {
        "test.yml": "data: !flatten [!flatten [[1, 2]], !flatten [[3, 4]]]",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["data"] == [1, 2, 3, 4]


def test_flatten_mixed_types(stage_files):
    """Test flattening with mixed data types."""
    files = {
        "test.yml": "data: !flatten [[1, 'two'], [3.0, True, null]]",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["data"] == [1, "two", 3.0, True, None]


def test_flatten_with_dicts(stage_files):
    """Test that dictionaries are not flattened (they should be preserved as elements)."""
    files = {
        "test.yml": "data: !flatten [[{'a': 1}], [{'b': 2}]]",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["data"] == [{"a": 1}, {"b": 2}]


def test_flatten_in_nested_structure(stage_files):
    """Test flattening within nested YAML structures."""
    files = {
        "test.yml": """
config:
  name: Test Config
  items: !flatten
    - [1, 2, 3]
    - [4, 5, 6]
  metadata:
    tags: !flatten
      - ['tag1', 'tag2']
      - ['tag3']
""",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["config"]["name"] == "Test Config"
    assert data["config"]["items"] == [1, 2, 3, 4, 5, 6]
    assert data["config"]["metadata"]["tags"] == ["tag1", "tag2", "tag3"]


def test_flatten_combined_with_references(stage_files):
    """Test flattening combined with !reference tags."""
    files = {
        "main.yml": """
data: !flatten
  - !reference { path: ./list1.yml }
  - !reference { path: ./list2.yml }
""",
        "list1.yml": "[1, 2, 3]",
        "list2.yml": "[4, 5, 6]",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "main.yml")
    assert data["data"] == [1, 2, 3, 4, 5, 6]


def test_flatten_combined_with_reference_all(stage_files):
    """Test flattening combined with !reference-all tags."""
    files = {
        "main.yml": """
data: !flatten
  - !reference-all { glob: ./lists/*.yml }
""",
        "lists/list1.yml": "[1, 2]",
        "lists/list2.yml": "[3, 4]",
        "lists/list3.yml": "[5, 6]",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "main.yml")
    assert data["data"] == [1, 2, 3, 4, 5, 6]


def test_parse_flatten_tag(stage_files):
    """Test that !flatten tags are parsed correctly without resolution."""
    files = {
        "test.yml": "data: !flatten [[1, 2], [3, 4]]",
    }
    stg = stage_files(files)
    data = parse_yaml_with_references(stg / "test.yml")
    assert isinstance(data["data"], Flatten)
    assert data["data"].sequence == [[1, 2], [3, 4]]


def test_flatten_sequences_function(stage_files):
    """Test the flatten_sequences function directly."""
    files = {
        "test.yml": """
nested:
  level1: !flatten
    - [1, 2]
    - !flatten [[3, 4]]
  level2: [5, 6]
""",
    }
    stg = stage_files(files)
    parsed = parse_yaml_with_references(stg / "test.yml")
    flattened = flatten_sequences(parsed)

    assert flattened["nested"]["level1"] == [1, 2, 3, 4]
    assert flattened["nested"]["level2"] == [5, 6]


def test_flatten_complex_nesting(stage_files):
    """Test complex nesting scenarios with flatten."""
    files = {
        "test.yml": """
result: !flatten
  - !flatten
    - [1, 2]
    - [3, 4]
  - !flatten [[5, 6]]
  - [7, 8]
""",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["result"] == [1, 2, 3, 4, 5, 6, 7, 8]


def test_flatten_preserves_order(stage_files):
    """Test that flattening preserves the order of elements."""
    files = {
        "test.yml": "data: !flatten [[1, 2], [3], [4, 5, 6], [7], [8, 9]]",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["data"] == [1, 2, 3, 4, 5, 6, 7, 8, 9]


def test_flatten_with_scalars(stage_files):
    """Test flattening with scalar values mixed in sequences."""
    files = {
        "test.yml": "data: !flatten [1, [2, 3], 4, [5, 6, 7]]",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["data"] == [1, 2, 3, 4, 5, 6, 7]


def test_flatten_mixed_objects_references(stage_files):
    """Test flattening a sequence of objects, references, and reference-all tags."""
    files = {
        "main.yml": """
CONTENTS: !flatten
  - {name: object-1}
  - {name: object-2}
  - !reference {path: objects/3.yaml}
  - !reference-all {glob: 'objects/v1/*.yaml'}
""",
        "objects/3.yaml": """
name: object-3
""",
        "objects/v1/object-4.yaml": """
- [{name: object-4}]
""",
        "objects/v1/object-5.yaml": """
- [{name: object-5}]
""",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "main.yml")

    expected = [
        {"name": "object-1"},
        {"name": "object-2"},
        {"name": "object-3"},
        {"name": "object-4"},
        {"name": "object-5"},
    ]

    assert data["CONTENTS"] == expected
