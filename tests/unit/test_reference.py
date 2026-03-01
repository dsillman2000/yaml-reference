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


@pytest.mark.parametrize(
    "test_name, files, entry_point",
    [
        (
            "self_reference",
            {
                "self_ref.yml": "data: !reference { path: ./self_ref.yml }",
            },
            "self_ref.yml",
        ),
        (
            "triangle_reference",
            {
                "file1.yml": "name: File 1\nref: !reference { path: ./file2.yml }",
                "file2.yml": "name: File 2\nref: !reference { path: ./file3.yml }",
                "file3.yml": "name: File 3\nref: !reference { path: ./file1.yml }",
            },
            "file1.yml",
        ),
        (
            "reference_all_circular",
            {
                "main.yml": "data: !reference-all { glob: ./refs/*.yml }",
                "refs/file1.yml": "name: File 1\nref: !reference { path: ../main.yml }",
                "refs/file2.yml": "name: File 2",
            },
            "main.yml",
        ),
        (
            "reference_all_self",
            {
                "main.yml": "data: !reference-all { glob: '*.yml' }",
                "doc-a.yml": "name: Doc A",
                "doc-b.yml": "name: Doc B",
            },
            "main.yml",
        ),
    ],
)
def test_circular_reference_detection(stage_files, test_name, files, entry_point):
    """Test that circular references are detected and disallowed."""
    stg = stage_files(files)

    with pytest.raises(ValueError, match="Circular reference detected"):
        load_yaml_with_references(stg / entry_point)


"""Test suite for anchor import behavior in yaml-reference."""


def test_anchor_reference_basic(stage_files):
    """Test that anchors can be used to import specific parts of a YAML file."""
    files = {
        "main.yml": "title: Main Document\nschema: !reference { path: ./schema.yml, anchor: config_schema }",
        "schema.yml": "other_data: unused\nconfig_schema: &config_schema\n  type: object\n  properties:\n    name: string",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "main.yml")
    assert data["title"] == "Main Document"
    assert data["schema"]["type"] == "object"
    assert data["schema"]["properties"]["name"] == "string"
    # Ensure other_data is not included
    assert "other_data" not in data["schema"]


def test_anchor_reference_scalar(stage_files):
    """Test that anchors work with scalar values."""
    files = {
        "main.yml": "db_host: !reference { path: ./config.yml, anchor: db_server }",
        "config.yml": "app_name: MyApp\ndb_server: &db_server localhost:5432\napi_key: secret123",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "main.yml")
    assert data["db_host"] == "localhost:5432"


def test_anchor_reference_list(stage_files):
    """Test that anchors work with list values."""
    files = {
        "main.yml": "servers: !reference { path: ./config.yml, anchor: server_list }",
        "config.yml": "description: Production Config\nserver_list: &server_list\n  - server1.com\n  - server2.com\n  - server3.com",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "main.yml")
    assert len(data["servers"]) == 3
    assert data["servers"][0] == "server1.com"
    assert data["servers"][1] == "server2.com"
    assert data["servers"][2] == "server3.com"


def test_anchor_not_found(stage_files):
    """Test that an error is raised when anchor is not found in the file."""
    files = {
        "main.yml": "data: !reference { path: ./config.yml, anchor: nonexistent }",
        "config.yml": "key: value\nother: data",
    }
    stg = stage_files(files)
    with pytest.raises(ValueError, match="Anchor 'nonexistent' not found"):
        load_yaml_with_references(stg / "main.yml")


def test_reference_all_with_anchor(stage_files):
    """Test that !reference-all works with anchors to import specific parts from multiple files."""
    files = {
        "main.yml": "configs: !reference-all { glob: ./services/*.yml, anchor: config }",
        "services/api.yml": "description: API Service\nconfig: &config\n  port: 3000\n  env: production",
        "services/db.yml": "description: Database Service\nconfig: &config\n  port: 5432\n  env: production",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "main.yml")
    assert len(data["configs"]) == 2
    # Both should have extracted configs
    configs = [c for c in data["configs"] if isinstance(c, dict) and "port" in c]
    assert len(configs) == 2
    ports = [c["port"] for c in configs]
    assert 3000 in ports
    assert 5432 in ports


def test_anchor_with_nested_content(stage_files):
    """Test that anchors correctly extract nested structures."""
    files = {
        "main.yml": "database: !reference { path: ./config.yml, anchor: db_config }",
        "config.yml": "name: Global Config\ndb_config: &db_config\n  primary:\n    host: localhost\n    port: 5432\n  replica:\n    host: replica.local\n    port: 5432",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "main.yml")
    assert data["database"]["primary"]["host"] == "localhost"
    assert data["database"]["replica"]["host"] == "replica.local"


def test_anchor_in_nested_reference(stage_files):
    """Test that anchors work in nested references (references within references)."""
    files = {
        "main.yml": "layer1: !reference { path: ./middle.yml }",
        "middle.yml": "layer2: !reference { path: ./config.yml, anchor: target }",
        "config.yml": "unused: ignored\ntarget: &target\n  core_value: success",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "main.yml")
    assert data["layer1"]["layer2"]["core_value"] == "success"


def test_parse_reference_with_anchor(stage_files):
    """Test that parse_yaml_with_references correctly identifies anchors in Reference objects."""
    files = {
        "main.yml": "data: !reference { path: ./config.yml, anchor: important }",
        "config.yml": "ignored: value\nimportant: &important\n  key: value",
    }
    stg = stage_files(files)
    data = parse_yaml_with_references(stg / "main.yml")
    assert isinstance(data["data"], Reference)
    assert data["data"].path == "./config.yml"
    assert data["data"].anchor == "important"


def test_parse_reference_all_with_anchor(stage_files):
    """Test that parse_yaml_with_references correctly identifies anchors in ReferenceAll objects."""
    files = {
        "main.yml": "items: !reference-all { glob: ./*.yml, anchor: item }",
        "doc1.yml": "item: &item value1",
        "doc2.yml": "item: &item value2",
    }
    stg = stage_files(files)
    data = parse_yaml_with_references(stg / "main.yml")
    assert isinstance(data["items"], ReferenceAll)
    assert data["items"].glob == "./*.yml"
    assert data["items"].anchor == "item"


def test_anchor_with_parse_yaml(stage_files):
    """Test parsing YAML with anchor parameter to extract specific anchor."""
    files = {
        "config.yml": "app_name: MyApp\nserver_config: &server_config\n  host: 0.0.0.0\n  port: 8000\napi_config: &api_config\n  timeout: 30",
    }
    stg = stage_files(files)
    # Parse with specific anchor
    data = parse_yaml_with_references(stg / "config.yml", anchor="server_config")
    assert data["host"] == "0.0.0.0"
    assert data["port"] == 8000
    assert "api_config" not in str(data)
    assert "app_name" not in str(data)


def test_parse_yaml_multiple_anchors_select_one(stage_files):
    """Test that parse_yaml_with_references extracts the correct anchor when multiple exist."""
    files = {
        "config.yml": "common: &common_config\n  debug: false\ndev: &dev_config\n  debug: true\n  db: local\nprod: &prod_config\n  debug: false\n  db: remote",
    }
    stg = stage_files(files)
    # Extract dev config
    dev_data = parse_yaml_with_references(stg / "config.yml", anchor="dev_config")
    assert dev_data["debug"] is True
    assert dev_data["db"] == "local"
    # Extract prod config
    prod_data = parse_yaml_with_references(stg / "config.yml", anchor="prod_config")
    assert prod_data["debug"] is False
    assert prod_data["db"] == "remote"


def test_anchor_reference_with_allow_paths(stage_files):
    """Test that anchor references respect allow_paths restrictions."""
    files = {
        "main.yml": "data: !reference { path: ./allowed/config.yml, anchor: data }",
        "allowed/config.yml": "data: &data\n  value: allowed",
        "forbidden/config.yml": "data: &data\n  value: forbidden",
    }
    stg = stage_files(files)
    # Should work with allowed path
    data = load_yaml_with_references(stg / "main.yml", allow_paths=[stg / "allowed"])
    assert data["data"]["value"] == "allowed"


def test_anchor_in_deeply_nested_structure(stage_files):
    """Test anchors in deeply nested YAML structures."""
    files = {
        "main.yml": "root: !reference { path: ./deep.yml, anchor: leaf }",
        "deep.yml": "outer:\n  middle:\n    inner:\n      leaf: &leaf\n        data: deep_value\n        list:\n          - item1\n          - item2",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "main.yml")
    assert data["root"]["data"] == "deep_value"
    assert len(data["root"]["list"]) == 2
    assert data["root"]["list"][0] == "item1"


def test_empty_anchor_list(stage_files):
    """Test that !reference-all with a missing anchor raises ValueError."""
    files = {
        "main.yml": "matching: !reference-all { glob: ./*.yml, anchor: target }",
        "file1.yml": "other: &other value1",
        "file2.yml": "different: &different value2",
    }
    stg = stage_files(files)
    with pytest.raises(ValueError, match="Anchor 'target' not found"):
        load_yaml_with_references(stg / "main.yml")


def test_anchor_reference_circular_detection(stage_files):
    """Test that circular references are detected even when using anchors."""
    files = {
        "file1.yml": "data: !reference { path: ./file2.yml, anchor: content }",
        "file2.yml": "content: &content\n  ref: !reference { path: ./file1.yml, anchor: data }",
    }
    stg = stage_files(files)
    with pytest.raises(ValueError, match="Circular reference detected"):
        load_yaml_with_references(stg / "file1.yml")


def test_anchor_with_yaml_aliases(stage_files):
    """Test that anchors work correctly with YAML aliases within the anchored content."""
    files = {
        "main.yml": "template: !reference { path: ./template.yml, anchor: config }",
        "template.yml": """base: &base_config
  project: Demo
config: &config !merge
  - *base_config
  - environment: production""",
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "main.yml")
    assert data["template"]["project"] == "Demo"
    assert data["template"]["environment"] == "production"


def test_anchor_reference_root_level(stage_files):
    """Test extracting a root-level anchor that contains nested anchored scalars.

    When a root-level anchor (&root) wraps a mapping whose values include nested
    anchors (e.g. &deep), the nested anchored events must still be included in the
    root anchor's event stream. Previously, the elif branch caused them to be
    skipped, leaving a mapping key with no value.
    """
    files = {
        "main.yml": (
            "whole: !reference { path: ./depth.yml, anchor: root }\n"
            "deep: !reference { path: ./depth.yml, anchor: deep }\n"
        ),
        "depth.yml": (
            "&root\nlevel1:\n  level2:\n    level3:\n      secret: &deep 42\n"
        ),
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "main.yml")
    assert data["whole"] == {"level1": {"level2": {"level3": {"secret": 42}}}}
    assert data["deep"] == 42


def test_anchor_reference_scalar_types(stage_files):
    """Test extracting scalar anchors for null, bool, and empty-string values.

    When a scalar like &emptyStr "" is extracted and re-emitted as a standalone
    document root, ruamel.yaml's emitter accesses event.ctag.handle.  If ctag is
    None the emitter crashes.  This test verifies that null, bool, and empty-string
    scalars can all be extracted via anchor references without error.
    """
    files = {
        "main.yml": (
            "a: !reference { path: ./scalars.yml, anchor: nullVal }\n"
            "b: !reference { path: ./scalars.yml, anchor: boolVal }\n"
            "c: !reference { path: ./scalars.yml, anchor: emptyStr }\n"
        ),
        "scalars.yml": (
            'nothing: &nullVal null\nflag: &boolVal true\nblank: &emptyStr ""\n'
        ),
    }
    stg = stage_files(files)
    data = load_yaml_with_references(stg / "main.yml")
    assert data["a"] is None
    assert data["b"] is True
    assert data["c"] == ""
