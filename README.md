# yaml-reference

Using `ruamel.yaml`, support cross-file references in YAML files using tags `!reference` and `!reference-all`.

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
from yaml_reference import YAML

yaml = YAML()
with open("root.yaml", "r") as f:
    data = yaml.load(f)
```

Note that the `YAML` class is a direct subclass of the base `ruamel.yaml.YAML` loader class, so the same API applies for customizing how it loads YAML files or other tags (e.g. `yaml = YAML(typ='safe')`).

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

## Anchor references

You can supply the `!reference` / `!reference-all` tags with an anchor name to use for the reference.

```yaml
# root.yaml
ports:
  !reference-all
  glob: "networks/*.yaml"
  anchor: "port"
```

```yaml
# networks/vpn.yaml
name: vpn
port: &port 8001
```

```yaml
# networks/nfs.yaml
name: nfs
port: &port 2000
```

Loading the `root.yaml` file with the Python interface or converting it with the CLI will result in the following YAML (in no particular order):

```yaml
ports:
  - 8001
  - 2000
```

## JMESPath functionality

You can also use JMESPath expressions to filter the results of references:

```yaml
# furthest.yml
furthest-town-name:
  !reference
  path: "towns/all.yml"
  jmespath: "max_by(towns, &distance).name"
```

```yaml
#towns/all.yml
towns:
  !reference-all
  glob: "towns/*.yml"
```

```yaml
# towns/los_altos.yml
name: Los Altos
distance: 10
# towns/sunnyvale.yml
name: Sunnyvale
distance: 5
# towns/mountain_view.yml
name: Mountain View
distance: 15
```

Using the CLI or Python interface for loading the root `furthes.yml` file will yield the following result:

```yaml
furthest-town-name: Mountain View
```

See more information about JMESPath expressions in the [JMESPath documentation](https://jmespath.org/).

## Acknowledgements

Author(s):

- David Sillman <dsillman2000@gmail.com>
  - Personal website: https://www.dsillman.com
