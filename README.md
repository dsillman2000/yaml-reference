# yaml-reference

Using `ruamel.yaml`, support cross-file references in YAML files using tags `!reference` and `!reference-all`.

Install the package from PyPI with:

```bash
# pip
pip install yaml-reference
# poetry
poetry add yaml-reference
# uv
uv add yaml-reference
```

## Spec

This Python library implements the YAML specification for cross-file references in YAML files using tags `!reference` and `!reference-all` as defined in the [yaml-reference-specs project](https://github.com/dsillman2000/yaml-reference-specs).

## Example

```yaml
# root.yaml
version: "3.1"
services:
  - !reference
    path: "services/website.yaml"

  - !reference
    path: "services/database.yaml"

networkConfigs:
  !reference-all
  glob: "networks/*.yaml"

```

Supposing there are `services/website.yaml` and `services/database.yaml` files in the same directory as `root.yaml`, and a `networks` directory with YAML files, the above will be expanded to account for the referenced files with the following Python code:

```python
from yaml_reference import YAMLReference

yaml = YAMLReference()
with open("root.yaml", "r") as f:
    data = yaml.load(f)
```

Note that the `YAMLReference` class is a direct subclass of the base `ruamel.yaml.YAML` loader class, so the same API applies for customizing how it loads YAML files or other tags (e.g. `yaml = YAMLReference(typ='safe')`).

### VSCode squigglies

To get red of red squigglies in VSCode when using the `!reference` and `!reference-all` tags, you can add the following to your `settings.json` file:

```json
    "yaml.customTags": [
        "!reference mapping",
        "!reference-all mapping"
    ]
```

## CLI interface

There is a CLI interface for this package which can be used to convert a YAML file which contains `!reference` tags into a single YAML file with all the references expanded. This is useful for generating a single file for deployment or other purposes. Note that the keys of mappings will be sorted alphabetically. This CLI interface is used to test the contract of this package against the `yaml-reference-specs` project.

```bash
$ yaml-reference-cli -h
  usage: yaml-reference-cli [-h] input_file

  Compile a YAML file containing !reference tags into a new YAML file with resolved references. Expects a YAML file to be provided via the "input_file" argument. Outputs JSON content to stdout.

  positional arguments:
    input_file  Path to the input YAML file with references to resolve and print as JSON.

  options:
    -h, --help  show this help message and exit
$ yaml-reference-cli root.yaml
  {
    "networkConfigs": [
      {
        "network": "vpn",
        "version": "1.1"
      },
      {
        "network": "nfs",
        "version": "1.0"
      }
    ],
    "services": [
      "website",
      "database"
    ],
    "version": "3.1"
  }
```

## Acknowledgements

Author(s):

- David Sillman <dsillman2000@gmail.com>
  - Personal website: https://www.dsillman.com
