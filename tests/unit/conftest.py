from pathlib import Path
from typing import Callable

import pytest


@pytest.fixture
def stage_files(tmp_path: Path) -> Callable[[dict[str, str]], Path]:
    """
    Fixture to create a temporary directory and stage files for testing.

    Args:
        tmp_path (Path): The temporary path provided by pytest.

    Returns:
        Callable[[dict[str, str]], Path]: A function that takes a dictionary of file names and contents,
                                          creates those files in a temporary directory, and returns the path.
    """

    def _stage_files(files: dict[str, str]) -> Path:
        """
        Create files in a temporary directory.

        Args:
            files (dict[str, str]): A dictionary where keys are file names and values are file contents.

        Returns:
            Path: The path to the temporary directory.
        """

        # Create a temporary directory
        staged_dir = tmp_path / "staged"
        staged_dir.mkdir(exist_ok=True)

        # Create files in the temporary directory
        for file_name, file_content in files.items():
            file_path = staged_dir / file_name
            if file_path.exists():
                # If the file already exists, remove it
                file_path.unlink()
            # Ensure the parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            # Write the file content
            with open(file_path, "w") as f:
                f.write(file_content)

        return staged_dir

    return _stage_files
