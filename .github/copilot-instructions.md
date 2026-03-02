# Copilot Instructions for yaml-reference

## Project Overview

**yaml-reference** is a Python library that extends `ruamel.yaml` with cross-file YAML composition using custom tags (`!reference`, `!reference-all`, `!flatten`, `!merge`). It's built to be a reference implementation of the [yaml-reference-specs](https://github.com/dsillman2000/yaml-reference-specs) specification.

## Build, Test, and Lint

**Tool chain:** `uv` (Python package manager) + `pytest` (testing) + `ruff` (linting/formatting)

### Install dependencies
```bash
uv sync
```

### Run all tests
```bash
uv run pytest tests/ -v
```

### Run a single test file
```bash
uv run pytest tests/unit/test_reference.py -v
```

### Run tests matching a pattern
```bash
uv run pytest tests/unit/test_reference.py::test_reference_load -v
```

### Run spec compliance tests (tests against yaml-reference-specs)
```bash
make spec-test
```

### Code formatting
```bash
uv run ruff format
# or
make format
```

### Linting and auto-fix
```bash
uv run ruff check --fix
# or
make lint
```

### Run full quality check (format + lint + test)
```bash
make check
```

### Build package
```bash
uv build
```

## Architecture

The library is structured in two key parts:

### Core Module (`yaml_reference/__init__.py`)
- **Reference & ReferenceAll classes**: Represent the `!reference` and `!reference-all` YAML tags as Python objects
- **parse_yaml_with_references()**: Parses YAML, returning Reference/ReferenceAll objects without resolving them (one layer only)
- **load_yaml_with_references()**: Fully recursively resolves all references, returning a complete Python dict
- **Flatten & Merge classes**: Represent `!flatten` and `!merge` tag logic
- **YAML loader setup**: Registers custom constructors with `ruamel.yaml.YAML` for each tag

### CLI Module (`yaml_reference/cli.py`)
- Simple entry point that calls the core loading functions
- Outputs JSON to stdout (compatible with spec tests)
- Takes optional `--allow` flag for path restrictions

### Test Structure (`tests/unit/`)
- `test_reference.py`: Tests for `!reference` and `!reference-all` tag resolution
- `test_flatten.py`: Tests for `!flatten` tag behavior
- `test_merge.py`: Tests for `!merge` tag behavior
- `conftest.py`: Pytest fixtures and test utilities

## Key Conventions & Design Patterns

### Security-First Path Handling
1. **Relative paths only**: All references must use relative paths (e.g., `path: "config/db.yaml"`). Absolute paths raise `ValueError`.
2. **Path restriction by default**: References can only access files in the same directory or subdirectories (no `..` to escape). Use `allow_paths` parameter to explicitly allow other directory trees.
3. **Security invariant**: Disallowed files are **never opened or read into memory**. Path filtering happens before file I/O.
4. **Silent omission (for `!reference-all`)**: When a glob pattern matches files outside allowed paths, those files are silently dropped from results and the function returns `rc=0` (not an error).

### YAML Tag Implementation Pattern
Each custom tag follows this pattern:
1. Define a class with `yaml_tag` attribute
2. Implement `@classmethod from_yaml(cls, constructor, node)` to parse from YAML
3. Register constructor with the YAML loader in `__init__.py`
4. The class instance persists through `parse_yaml_with_references()`, allowing layer-by-layer resolution

### Reference Resolution Order
1. **Circular reference detection** occurs during recursive resolution by tracking a "resolution stack"
2. **Anchors** (optional parameter): If specified, extract only the anchored section from the referenced file
3. **Recursive expansion**: `load_yaml_with_references()` recursively expands all tags, applying `!flatten` and `!merge` logic as it encounters them

### Error Handling
- **ValueError** for spec violations: absolute paths, circular references, invalid anchors
- **FileNotFoundError** for missing referenced files
- **Glob errors**: Return empty list `[]` if glob matches no files (silent omission)

### Spec Compliance Testing
The project tests against `yaml-reference-specs`, a Go-based reference implementation. The spec tests verify:
- Correct expansion of all four tags
- Proper error detection (bad paths, missing files, circular refs)
- Path restriction enforcement
- Edge cases like empty globs and nested composition

Run with: `make spec-test` or `scripts/spec-test.sh`

## Pre-commit Hooks

The repository enforces conventional commits and code quality via pre-commit:
- **ruff-check** and **ruff-format**: Ensures consistent style
- **conventional-pre-commit**: Enforces Conventional Commits format (e.g., `feat:`, `fix:`, `docs:`)
- Standard hooks: trailing whitespace, EOF fixers, YAML validation

Install hooks with: `pre-commit install`

## Common Workflows

### Adding a new tag type
1. Create a class in `yaml_reference/__init__.py` with `yaml_tag` attribute and `from_yaml()` classmethod
2. Register the constructor after the class definition
3. Add resolution logic (handle in recursive expansion)
4. Write tests in `tests/unit/test_*.py` following existing patterns
5. Update README.md with usage example

### Debugging a reference resolution issue
1. Use `parse_yaml_with_references()` to see raw Reference objects before resolution
2. Add print statements or use a debugger to trace the `_resolve_references()` recursive calls
3. Check the resolution stack to verify circular reference detection is working
4. Run a specific test with `-v` flag to see detailed assertion output

### Updating error messages
Ensure error messages follow this pattern: include the problematic value, the path of the file where the error occurred, and the specific constraint violated. This helps spec tests verify proper error handling.
