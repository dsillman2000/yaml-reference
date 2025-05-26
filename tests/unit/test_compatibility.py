import pytest


@pytest.mark.parametrize(
    "typ",
    [
        "rt",
        "safe",
        # "unsafe", # Pending deprecation
        "base",
    ],
)
def test_typ_values(typ: str, stage_files):
    from yaml_reference import YAML

    yaml = YAML(typ=typ)

    files = {
        "test.yml": "hello: !reference { path: data.yml }\n",
        "data.yml": "world: Earth\n",
    }
    stg = stage_files(files)
    data = yaml.load(stg / "test.yml")
    assert data
    assert data["hello"] == {"world": "Earth"}
