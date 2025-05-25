# yaml-reference

Using `ruamel.yaml`, support cross-file references in YAML files using tags `!reference` and `!reference-all`.

## Example

```yaml
# root.yaml
version: "3.1"
services:
  - !reference {
    path: "services/website.yaml"
  }
  - !reference {
    path: "services/database.yaml"
  }
networkConfigs: !reference-all { glob: "networks/*.yaml" }
```

Supposing there are `services/website.yaml` and `services/database.yaml` files in the same directory as `root.yaml`, and a `networks` directory with YAML files, the above will be expanded to account for the referenced files with the following Python code:

```python
from yaml_reference import YAML

yaml = YAML()
with open("root.yaml", "r") as f:
    data = yaml.load(f)
```

Note that the `YAML` class is a direct subclass of the base `ruamel.yaml.YAML` loader class, so the same API applies for customizing how it loads YAML files or other tags.

## Acknowledgements

Author(s):

- David Sillman <dsillman2000@gmail.com>
  - Personal website: https://www.dsillman.com
