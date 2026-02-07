def test_compile_cli_basic(stage_files):
    from yaml_reference.cli import compile_main

    files = {
        "test.yml": "another_inner: !reference { path: deeper/inner2.yml }\n",
        "deeper/inner2.yml": "inner2: inner2_value\n",
        "deeper/yet/inner3.yml": "inner3: inner3_value\n",
        "deeper/yet/leaf.yml": "leaf_value\n",
    }
    stg = stage_files(files)
    input_file, output_file = (stg / "test.yml"), (stg / "compiled.yml")
    compile_main(str(input_file), str(output_file))
    assert output_file.exists()
    content_out = output_file.read_text()
    assert content_out == "another_inner:\n  inner2: inner2_value\n"

    files["test.yml"] += "\ninner_again: !reference-all { glob: deeper/yet/*.yml }\n"
    stg = stage_files(files)
    input_file, output_file = (stg / "test.yml"), (stg / "compiled.yml")
    compile_main(str(input_file), str(output_file))
    assert output_file.exists()
    content_out = output_file.read_text()
    assert content_out == (
        "another_inner:\n"
        "  inner2: inner2_value\n"
        "inner_again:\n"
        "- inner3: inner3_value\n"
        "- leaf_value\n"
    )


def test_reference_all_purges_anchors(stage_files):
    from yaml_reference.cli import compile_main

    files = {
        "test.yml": "names:\n  !reference-all\n  glob: tests/*.yml\n",
        "tests/test1.yml": "name: test1\ndate: &test-date 2025-01-01\nscore: &score 99\n",
        "tests/test2.yml": "name: test2\ndate: &test-date 2025-01-02\nscore: &score 98\n",
        "tests/test3.yml": "name: test3\ndate: &test-date 2025-02-01\nscore: &score 90\n",
    }
    stg = stage_files(files)
    input_file, output_file = (stg / "test.yml"), (stg / "compiled.yml")
    compile_main(str(input_file), str(output_file))
    assert output_file.exists()
    content_out = output_file.read_text()
    assert content_out.startswith("names:\n")
    assert "name: test1" in content_out
    assert "name: test2" in content_out
    assert "name: test3" in content_out
    assert "date: 2025-01-01" in content_out
    assert "date: 2025-01-02" in content_out
    assert "date: 2025-02-01" in content_out
    assert "score: 99" in content_out
    assert "score: 98" in content_out
    assert "score: 90" in content_out
    # Assert no anchors are present in the output
    assert "date: &test-date" not in content_out
    assert "score: &score" not in content_out
