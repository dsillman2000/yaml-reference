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
from yaml_reference import load_yaml_with_references

data = load_yaml_with_references("root.yaml")
print(data)
# {"networkConfigs": [{"network": "vpn","version": "1.1"},{"network": "nfs","version": "1.0"}],"services": ["website","database"],"version": "3.1"}

# With path restrictions for security
data = load_yaml_with_references("root.yaml", allow_paths=["/allowed/path"])
```

Note that the `load_yaml_with_references` function instantiates a `ruamel.yaml.YAML` loader class (`typ='safe'`) to perform the deserialization of the YAML files, and returns a Python dictionary with the recursively-expanded YAML data.

If you wish to resolve one "layer" of references without recursively exhausting the entire reference graph, the `parse_yaml_with_references` function can be used to obtain the original YAML document's contents with `!reference`/`!reference-all` tags as dedicated objects called `Reference` and `ReferenceAll`.

```python
from yaml_reference import parse_yaml_with_references

data = parse_yaml_with_references("root.yaml")
print(data["networkConfigs"])
# ReferenceAll(glob="networks/*.yaml", location="/path/to/root.yaml")

# With path restrictions for security
data = parse_yaml_with_references("root.yaml", allow_paths=["/allowed/path"])
```

### VSCode squigglies

To get red of red squigglies in VSCode when using the `!reference` and `!reference-all` tags, you can add the following to your `settings.json` file:

```json
    "yaml.customTags": [
        "!reference mapping",
        "!reference-all mapping"
    ]
```

## CLI interface

There is a CLI interface for this package which can be used to read a YAML file which contains `!reference` tags and dump its contents as pretty-printed JSON with references expanded. This is useful for generating a single file for deployment or other purposes. Note that the keys of mappings will be sorted alphabetically. This CLI interface is used to test the contract of this package against the `yaml-reference-specs` project.

```bash
$ yaml-reference-cli -h
  usage: yaml-reference-cli [-h] [--allow ALLOW_PATHS] input_file

  Compile a YAML file containing !reference tags into a new YAML file with resolved references. Expects a YAML file to be provided via the "input_file" argument.
  Outputs JSON content to stdout.

  positional arguments:
    input_file           Path to the input YAML file with references to resolve and print as JSON.

  options:
     -h, --help           show this help message and exit
     --allow ALLOW_PATHS  Path to allow references from.

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

It's still possible to yield the results as a YAML file using the `yq` CLI tool ([mikefarah/yq](https://github.com/mikefarah/yq)).

```bash
$ yaml-reference-cli root.yaml | yq -P
networkConfigs:
  - network: vpn
    version: 1.1
  - network: nfs
    version: 1.0
services:
  - website
  - database
version: 3.1
# Pipe it to a result file
$ yaml-reference-cli root.yaml | yq -P > .compiled/root.yaml
```

## Circular reference protection

As required by the yaml-reference-specs specification, this package includes circular reference detection to prevent infinite recursion. If a circular reference is detected (e.g., A references B, B references C, C references A), a `ValueError` will be raised with a descriptive error message. This protects against self-references and circular chains in both `!reference` and `!reference-all` tags.

## Security considerations

### Path restriction and `allow_paths`

By default, `!reference` and `!reference-all` tags can only reference files within the same directory as the source YAML file (or child subdirectories). To allow references to files in other disparate directory trees, you must explicitly specify allowed paths using the `allow_paths` parameter:

```python
from yaml_reference import load_yaml_with_references

# Allow references from specific directories only
data = load_yaml_with_references(
    "config.yml",
    allow_paths=["/allowed/path1", "/allowed/path2"]
)
```

In the CLI, use the `--allow` flag:

```bash
yaml-reference compile input.yml --allow /allowed/path1 --allow /allowed/path2
```

Whether or not `allow_paths` is specified, the default behavior is to allow references to files in the same directory as the source YAML file (or subdirectories). "Back-navigating" out of a the root directory is not allowed (".." local references in a root YAML file). This provides a secure baseline to prevent unsafe access which is not explicitly allowed.

### Absolute path restrictions

References using absolute paths (e.g., `/tmp/file.yml`) are explicitly rejected with a `ValueError`. All reference paths must be relative to the source file's directory. If you absolutely must reference an absolute path, relative paths to symlinks can be used. Note that their target directories must be explicitly allowed to avoid permission errors (see the above section about "Path restriction and `allow_paths`").

## Acknowledgements

Contributor(s):

- David Sillman <dsillman2000@gmail.com>
  - Personal website: https://www.dsillman.com
- Ryan Johnson
