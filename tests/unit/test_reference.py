from yaml_reference import YAMLReference


def test_reference_load(stage_files):

    yaml = YAMLReference()

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
    yaml = YAMLReference()

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
