import os
import yaml
import logging
import joblib
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()



def read_yaml(path_to_yaml: Path) -> dict:
    """Reads a YAML file and returns its contents as a dictionary."""
    try:
        with open(path_to_yaml, 'r', encoding='utf-8') as yaml_file:
            content = yaml.safe_load(yaml_file)
            logging.info(f"yaml file: {path_to_yaml} loaded successfully")
            return content
    except Exception as e:
        logging.error(f"Error reading YAML file {path_to_yaml}: {e}")
        raise e


def create_directories(path_to_directories: list, verbose=True):
    """Creates a list of directories if they don't exist."""
    for path in path_to_directories:
        os.makedirs(path, exist_ok=True)
        if verbose:
            logging.info(f"Created directory at: {path}")


def save_bin(data: Any, path: Path):
    """Saves data as a binary file using joblib."""
    joblib.dump(value=data, filename=path)
    logging.info(f"Binary file saved at: {path}")


def _validate_file_path(path: Path, max_size_mb: int = 500) -> None:
    # Resolve to absolute path
    resolved_path = path.resolve()
    
    # Check file exists and is a regular file
    if not resolved_path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    if not resolved_path.is_file():
        raise ValueError(f"Path is not a regular file: {path}")
    
    # Check file size to prevent DoS from huge files
    file_size_mb = resolved_path.stat().st_size / (1024 * 1024)
    if file_size_mb > max_size_mb:
        raise ValueError(f"File too large: {file_size_mb:.1f}MB (max {max_size_mb}MB)")


def load_bin(path: Path) -> Any:
    """Loads a binary file using joblib with security validation."""
    _validate_file_path(path)
    data = joblib.load(path)
    logging.info(f"Binary file loaded from: {path}")
    return data



def get_size(path: Path) -> str:
    """Returns the size of a file in KB."""
    size_in_kb = round(os.path.getsize(path) / 1024)
    return f"~ {size_in_kb} KB"


def get_project_root() -> Path:
    """Returns the project root directory based on this file's location."""
    # src/utils/common.py -> src/utils -> src -> project_root
    return Path(__file__).resolve().parent.parent.parent


def get_env_var(key: str, default: str = None) -> str:
    
    value = os.getenv(key, default)
    if value is None:
        logging.warning(f"Environment variable '{key}' not found.")
    return value
