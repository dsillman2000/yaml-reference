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
