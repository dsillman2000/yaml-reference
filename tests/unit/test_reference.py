def test_reference_load(stage_files):
    from yaml_reference import YAML

    yaml = YAML()

    files = {
        "test.yml": "hello: world\ncontents: !reference { path: ./inner.yml }",
        "inner.yml": "inner: inner_value\ninner_list:\n  - inner_list_value_1\n  - inner_list_value_2",
    }
    stg = stage_files(files)
    data = yaml.load(stg / "test.yml")
    assert data["hello"] == "world"
    assert data["contents"]["inner"] == "inner_value"

    files["inner.yml"] += "\nanother_inner: !reference { path: deeper/inner2.yml }"
    files["deeper/inner2.yml"] = "inner2: inner2_value"
    stg = stage_files(files)
    data = yaml.load(stg / "test.yml")
    assert data["hello"] == "world"
    assert data["contents"]["inner"] == "inner_value"
    assert data["contents"]["another_inner"]["inner2"] == "inner2_value"

    files["deeper/inner2.yml"] += (
        "\nanother_inner2: !reference { path: yet/inner3.yml }"
    )
    files["deeper/yet/inner3.yml"] = "inner3: inner3_value"
    stg = stage_files(files)
    data = yaml.load(stg / "test.yml")
    assert (
        data["contents"]["another_inner"]["another_inner2"]["inner3"] == "inner3_value"
    )

    files["leaf.yml"] = "leaf_value\n..."
    files["deeper/yet/inner3.yml"] += "\nleaf: !reference { path: ../../leaf.yml }"
    stg = stage_files(files)
    data = yaml.load(stg / "test.yml")
    assert data["contents"]["another_inner"]["another_inner2"]["leaf"] == "leaf_value"


def test_reference_all_load(stage_files):
    from yaml_reference import YAML

    yaml = YAML()

    files = {
        "test.yml": "hello: world\ncontents: !reference-all { glob: ./chapters/*.yml }",
        "chapters/chapter1.yml": "chapter_value: 1\n",
        "chapters/chapter2.yml": "chapter_value: 2\n",
        "chapters/chapter3.yml": "chapter_value: 3\n",
    }
    stg = stage_files(files)
    data = yaml.load(stg / "test.yml")
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
    data = yaml.load(stg / "test.yml")
    assert data
    assert len(data["inner"]["open"]) == 2
    assert {"chapter1_summary": 1} in data["inner"]["open"]
    assert {"chapter2_summary": 2} in data["inner"]["open"]


def test_reference_anchor_load(stage_files):
    from yaml_reference import YAML

    yaml = YAML()

    files = {
        "test.yml": "hello: world\ncontents: !reference { path: ./inner.yml, anchor: inner }",
        "inner.yml": "inner: &inner inner_value\ninner_list:\n  - inner_list_value_1\n  - inner_list_value_2",
    }
    stg = stage_files(files)
    data = yaml.load(stg / "test.yml")
    assert data["hello"] == "world"
    assert data["contents"] == "inner_value"

    files["inner.yml"] = "data: &inner !reference { path: deeper/inner2.yml }\n"
    files["deeper/inner2.yml"] = "inner2: inner2_value"
    stg = stage_files(files)
    data = yaml.load(stg / "test.yml")
    assert data["contents"] == {"inner2": "inner2_value"}

    files["deeper/inner2.yml"] = "data: !reference { path: inner3.yml, anchor: yo }\n"
    files["deeper/inner3.yml"] = (
        "inner3: inner3_value\nmore: &yo\n  type: xyz\n  information: [1, 2, 3]\n"
    )
    stg = stage_files(files)
    data = yaml.load(stg / "test.yml")
    assert data["contents"] == {"data": {"type": "xyz", "information": [1, 2, 3]}}


def test_reference_all_anchor_load(stage_files):
    from yaml_reference import YAML

    yaml = YAML()

    files = {
        "test.yml": "hello: world\ncontents: !reference-all { glob: ./chapters/*.yml, anchor: chapter }",
        "chapters/chapter1.yml": "chapter_value: 1\nchapter_content: &chapter |-\n  Lorem ipsum dolor sit amet,\n  consectetur adipiscing elit.\n",
        "chapters/chapter2.yml": "chapter_value: 2\nchapter_content: &chapter |-\n  Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.\n",
        "chapters/chapter3.yml": "chapter_value: 3\nchapter_content: &chapter |-\n  Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris\n  nisi ut aliquip ex ea commodo consequat.\n",
    }
    stg = stage_files(files)
    data = yaml.load(stg / "test.yml")
    assert data
    assert data["hello"] == "world"
    assert len(data["contents"]) == 3
    assert (
        "Lorem ipsum dolor sit amet,\nconsectetur adipiscing elit." in data["contents"]
    )
    assert (
        "Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua."
        in data["contents"]
    )
    assert (
        "Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris\nnisi ut aliquip ex ea commodo consequat."
        in data["contents"]
    )


def test_reference_jmespath_load(stage_files):
    from yaml_reference import YAML

    yaml = YAML()

    files = {
        "test.yml": "item: !reference\n  path: data.yml\n  jmespath: items[?name=='item1']",
        "data.yml": "items:\n  - name: item1\n    value: value1\n  - name: item2\n    value: value2\n",
    }
    stg = stage_files(files)
    data = yaml.load(stg / "test.yml")
    assert data["item"] == [{"name": "item1", "value": "value1"}]

    files["data.yml"] = "items:\n  !reference-all\n  glob: items/item-*.yml\n"
    files["items/item-1.yml"] = "name: item1\nvalue: value1\n"
    files["items/item-2.yml"] = "name: item2\nvalue: value2\n"
    files["items/item-3.yml"] = "name: item3\nvalue: value3\n"
    files["test.yml"] = (
        "item: !reference\n  path: data.yml\n  jmespath: items[?name=='item1'] | [0]"
    )
    stg = stage_files(files)
    data = yaml.load(stg / "test.yml")
    assert data["item"] == {"name": "item1", "value": "value1"}

    files["test.yml"] = (
        "item: !reference\n  path: data.yml\n  jmespath: max_by(items, &value)"
    )
    stg = stage_files(files)
    data = yaml.load(stg / "test.yml")
    assert data["item"] == {"name": "item3", "value": "value3"}


def test_reference_all_jmespath_load(stage_files):
    from yaml_reference import YAML

    yaml = YAML()

    files = {
        "test.yml": "items: !reference-all\n  glob: ./data/*.yml\n  jmespath: name",
        "data/item1.yml": "name: item1\nvalue: value1\n",
        "data/item2.yml": "name: item2\nvalue: value2\n",
        "data/item3.yml": "name: item3\nvalue: value3\n",
    }
    stg = stage_files(files)
    data = yaml.load(stg / "test.yml")
    assert len(data["items"]) == 3
    assert "item1" in data["items"]
    assert "item2" in data["items"]
    assert "item3" in data["items"]
