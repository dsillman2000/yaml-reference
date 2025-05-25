install:
	@echo "Installing dependencies..."
	@poetry install
	@echo "Dependencies installed."

test:
	@echo "Running tests..."
	@poetry run pytest
	@echo "Tests completed."
