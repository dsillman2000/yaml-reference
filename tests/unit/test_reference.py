def test_reference_load(stage_files):
    from yaml_reference import yaml

    files = {
        "test.yml": """hello: world\ncontents: !reference { path: ./inner.yml }""",
        "inner.yml": """inner: inner_value\ninner_list:\n  - inner_list_value_1\n  - inner_list_value_2""",
    }
    stg = stage_files(files)
    data = yaml.load(stg / "test.yml")
    assert data["hello"] == "world"
    assert data["contents"]["inner"] == "inner_value"

    files["inner.yml"] += "\nanother_inner: !reference { path: deeper/inner2.yml }"
    files["deeper/inner2.yml"] = """inner2: inner2_value"""
    stg = stage_files(files)
    data = yaml.load(stg / "test.yml")
    assert data["hello"] == "world"
    assert data["contents"]["inner"] == "inner_value"
    assert data["contents"]["another_inner"]["inner2"] == "inner2_value"

    files["deeper/inner2.yml"] += "\nanother_inner2: !reference { path: yet/inner3.yml }"
    files["deeper/yet/inner3.yml"] = """inner3: inner3_value"""
    stg = stage_files(files)
    data = yaml.load(stg / "test.yml")
    assert data["contents"]["another_inner"]["another_inner2"]["inner3"] == "inner3_value"
