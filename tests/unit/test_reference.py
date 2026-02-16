from pathlib import Path

import pytest

from yaml_reference import (
    Reference,
    ReferenceAll,
    load_yaml_with_references,
    parse_yaml_with_references,
)


def test_reference_load(stage_files):

    files = {
        "test.yml": "hello: world\ncontents: !reference { path: ./inner.yml }",
        "inner.yml": "inner: inner_value\ninner_list:\n  - inner_list_value_1\n  - inner_list_value_2",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["hello"] == "world"
    assert data["contents"]["inner"] == "inner_value"

    files["inner.yml"] += "\nanother_inner: !reference { path: deeper/inner2.yml }"
    files["deeper/inner2.yml"] = "inner2: inner2_value"
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["hello"] == "world"
    assert data["contents"]["inner"] == "inner_value"
    assert data["contents"]["another_inner"]["inner2"] == "inner2_value"

    files["deeper/inner2.yml"] += (
        "\nanother_inner2: !reference { path: yet/inner3.yml }"
    )
    files["deeper/yet/inner3.yml"] = "inner3: inner3_value"
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert (
        data["contents"]["another_inner"]["another_inner2"]["inner3"] == "inner3_value"
    )

    files["leaf.yml"] = "leaf_value\n..."
    files["deeper/yet/inner3.yml"] += "\nleaf: !reference { path: ../../leaf.yml }"
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data["contents"]["another_inner"]["another_inner2"]["leaf"] == "leaf_value"


def test_reference_all_load(stage_files):
    files = {
        "test.yml": "hello: world\ncontents: !reference-all { glob: ./chapters/*.yml }",
        "chapters/chapter1.yml": "chapter_value: 1\n",
        "chapters/chapter2.yml": "chapter_value: 2\n",
        "chapters/chapter3.yml": "chapter_value: 3\n",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data
    assert data["hello"] == "world"
    assert len(data["contents"]) == 3
    assert {"chapter_value": 1} in data["contents"]
    assert {"chapter_value": 2} in data["contents"]
    assert {"chapter_value": 3} in data["contents"]

    files = {
        "test.yml": "inner: !reference { path: next/open.yml }\n",
        "next/open.yml": "open: !reference-all { glob: ../chapters/*/summary.yml }\n",
        "chapters/chapter1/summary.yml": "chapter1_summary: 1\n",
        "chapters/chapter2/summary.yml": "chapter2_summary: 2\n",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "test.yml")
    assert data
    assert len(data["inner"]["open"]) == 2
    assert {"chapter1_summary": 1} in data["inner"]["open"]
    assert {"chapter2_summary": 2} in data["inner"]["open"]


def test_parse_references(stage_files):
    files = {
        "test.yml": "inner: !reference { path: next/open.yml }\n",
        "next/open.yml": "open: !reference-all { glob: ../chapters/*/summary.yml }\n",
        "chapters/chapter1/summary.yml": "chapter1_summary: 1\n",
        "chapters/chapter2/summary.yml": "chapter2_summary: 2\n",
    }
    stg = stage_files(files)
    data = parse_yaml_with_references(stg / "test.yml")
    assert data
    assert data["inner"] is not None
    assert isinstance(data["inner"], Reference)
    assert data["inner"].path == "next/open.yml"
    assert hasattr(data["inner"], "location")
    assert data["inner"].location == str((stg / "test.yml").absolute())

    ref_loc = Path(data["inner"].location)
    ref_path = data["inner"].path
    data = parse_yaml_with_references(ref_loc.parent / ref_path)
    assert data
    assert data["open"] is not None
    assert isinstance(data["open"], ReferenceAll)
    assert data["open"].glob == "../chapters/*/summary.yml"
    assert data["open"].location == str((stg / "next/open.yml").absolute())


def test_disallow_absolute_path_references(stage_files):
    """Test that absolute path references are disallowed."""
    actual_file = Path("/tmp/file.yml")
    if actual_file.exists():
        actual_file.unlink()
    actual_file.write_text("data: hello world")

    files = {"input.yml": "data: !reference { path: '/tmp/file.yml' }"}
    stg = stage_files(files)

    with pytest.raises(ValueError):
        # When omitting allowed paths, the reference should fail due to absolute path.
        load_yaml_with_references(stg / "input.yml")

    with pytest.raises(ValueError):
        # Even if we explicitly allow the /tmp folder, we don't allow absolute paths in references.
        load_yaml_with_references(stg / "input.yml", allow_paths=["/tmp"])


def test_allow_paths_load_yaml_with_references(stage_files):
    """Test that allow_paths restricts which paths can be referenced."""
    files = {
        "inner/test.yml": "hello: world\ncontents: !reference { path: ./inner.yml }",
        "inner/another_test.yml": "hello: world\nout: !reference { path: ../outside/outside.yml }",
        "inner/with_all.yml": "all: !reference-all {glob: '../outside/*.yml'}",
        "inner/inner.yml": "inner: inner_value",
        "outside/outside.yml": "outside: outside_value",
        "some/other.yml": "other: other_value",
    }
    stg = stage_files(files)

    # Test with default allow_paths (should work since inner.yml is in same directory)
    data = load_yaml_with_references(stg / "inner/test.yml")
    assert data["hello"] == "world"
    assert data["contents"]["inner"] == "inner_value"

    # Test with explicit allow_paths that includes the "outside" dir (!reference)
    data = load_yaml_with_references(
        stg / "inner/another_test.yml", allow_paths=[stg / "outside"]
    )
    assert data["hello"] == "world"
    assert data["out"]["outside"] == "outside_value"

    # Test with allow_paths that doesn't include the referenced file (should fail, !reference)
    with pytest.raises(PermissionError):
        load_yaml_with_references(stg / "inner/another_test.yml")

    # Test with explicit allow_paths that includes the "outside" dir (!reference-all)
    data = load_yaml_with_references(
        stg / "inner/with_all.yml", allow_paths=[stg / "outside"]
    )
    assert data["all"][0]["outside"] == "outside_value"

    # Test with allow_paths that doesn't include the referenced file (should fail, !reference-all)
    with pytest.raises(PermissionError):
        load_yaml_with_references(
            stg / "inner/with_all.yml", allow_paths=[stg / "some"]
        )
