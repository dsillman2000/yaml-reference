install:
	@echo "Installing dependencies..."
	@uv sync
	@echo "Dependencies installed."

test:
	@echo "Running tests..."
	@uv run pytest
	@echo "Tests completed."

spec-test:
	@echo "Running spec tests..."
	@go install github.com/dsillman2000/yaml-reference-specs@latest
	@YAML_REFERENCE_CLI_EXECUTABLE=$$PWD/.venv/bin/yaml-reference-cli yaml-reference-specs
	@echo "Spec tests completed."

format:
	@echo "Formatting code..."
	@uv run ruff format
	@echo "Formatting completed."

lint:
	@echo "Linting code..."
	@uv run ruff check --fix
	@echo "Linting completed."

check: format lint test

clean:
	@echo "Cleaning up..."
	@rm -rf .pytest_cache
	@rm -rf .ruff_cache
	@rm -rf build
	@rm -rf dist
	@rm -rf *.egg-info
	@echo "Cleaning completed."

build:
	@echo "Building package..."
	@uv build
	@echo "Build completed."

publish: build
	@echo "Publishing to PyPI..."
	@uv publish
	@echo "Publish completed."
