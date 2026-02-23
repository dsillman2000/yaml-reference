# yaml-reference

Using `ruamel.yaml`, support cross-file references and YAML composition in YAML files using tags `!reference`, `!reference-all`, `!flatten`, and `!merge`.

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
![Spec Status](https://img.shields.io/badge/spec%20v0.2.5--1-passing-brightgreen?link=https%3A%2F%2Fgithub.com%2Fdsillman2000%2Fyaml-reference-specs%2Ftree%2Fv0.2.5-1)

This Python library implements the YAML specification for cross-file references and YAML composition in YAML files using tags `!reference`, `!reference-all`, `!flatten`, and `!merge` as defined in the [yaml-reference-specs project](https://github.com/dsillman2000/yaml-reference-specs).

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

tags: !flatten
  - !reference { path: "common/tags.yaml" }
  - "web"
  - "service"

config: !merge
  - !reference { path: "config/defaults.yaml" }
  - !reference { path: "config/overrides.yaml" }

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

### The `!merge` Tag

The `!merge` tag combines multiple YAML mappings (dictionaries) into a single mapping. This is useful for composing configuration from multiple sources or applying overrides. When you use `!merge`, you provide a sequence of mappings that will be merged together, with later mappings overriding keys from earlier ones.

```yaml
# Example: Merge default and override configurations
config: !merge
  - {host: "localhost", port: 8080, debug: false}
  - {port: 9000, debug: true}  # Overrides port and debug from the first mapping
```

When loaded with `load_yaml_with_references`, this becomes `{"host": "localhost", "port": 9000, "debug": true}`. The `!merge` tag can also be nested and combined with `!reference` and `!flatten` tags for complex YAML composition scenarios.

Note that, if a nested sequence of mappings is provided to `!merge`, the sequence argument will be flattened first, and then the resulting mappings will be merged together. For example:

```yaml
config: !merge
  - - a: 1
    - b: 2
  - c: 3
  - - [{c: 5, a: 5}]
```

Will be processed into `{"config": {"a": 5, "b": 2, "c": 5}}` because the nested sequence of mappings will be flattened into a single sequence of mappings before merging.

### VSCode squigglies

To get rid of red squigglies in VSCode when using the `!reference`, `!reference-all`, `!flatten`, and `!merge` tags, you can add the following to your `settings.json` file:

```json
    "yaml.customTags": [
        "!reference mapping",
        "!reference-all mapping",
        "!flatten sequence",
        "!merge sequence"
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
    "tags": [
      "common:aws",
      "common:http",
      "common:security",
      "common:waf",
      "web",
      "service"
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
tags:
  - common:aws
  - common:http
  - common:security
  - common:waf
  - web
  - service
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
