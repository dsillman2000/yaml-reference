from yaml_reference import load_yaml_with_references


def test_multi_document_root_file_loads_as_array(stage_files):
    files = {
        "root.yml": """
---
service: !reference { path: ./service.yml }
---
ignored_only: !ignore true
--- !ignore
drop_me: true
---
items: !flatten
  - !reference-all { glob: ./entries.yml }
---
config: !merge
  - {a: 1}
  - !reference-all { glob: ./patches.yml }
""",
        "service.yml": "name: api\n",
        "entries.yml": "---\n- [1, 2]\n---\n- [3, 4]\n",
        "patches.yml": "---\na: 2\n---\nb: 3\n",
    }
    stg = stage_files(files)

    data = load_yaml_with_references(stg / "root.yml")

    assert data == [
        {"service": {"name": "api"}},
        {},
        {"items": [1, 2, 3, 4]},
        {"config": {"a": 2, "b": 3}},
    ]
