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

## CLI interface

There is a CLI interface for this package which can be used to convert a YAML file which contains `!reference` tags into a single YAML file with all the references expanded. This is useful for generating a single file for deployment or other purposes.

```bash
$ yref-compile -h
  usage: yref-compile [-h] [-i INPUT] [-o OUTPUT]

  Compile a YAML file containing !reference tags into a new YAML file with resolved references.

  options:
    -h, --help            show this help message and exit
    -i INPUT, --input INPUT
                          Path to the input YAML file. If not provided, reads from stdin.
    -o OUTPUT, --output OUTPUT
                          Path to the output YAML file. If not provided, writes to stdout.
$ yref-compile -i root.yaml
  version: '3.1'
  services:
  - website
  - database
  networkConfigs:
  - network: vpn
    version: 1.1
  - network: nfs
    version: 1.0
```

## Acknowledgements

Author(s):

- David Sillman <dsillman2000@gmail.com>
  - Personal website: https://www.dsillman.com
