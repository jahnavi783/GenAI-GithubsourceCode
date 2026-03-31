"""
Centralised .env loader.

Finds the .env file relative to this file's location so it always works
regardless of which directory uvicorn / the terminal is launched from.
Import and call load_env() at the top of every module instead of bare load_dotenv().
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Absolute path to the project root .env
_ENV_PATH = Path(__file__).resolve().parent / ".env"


def load_env() -> None:
    """Load .env with override=True using an absolute path."""
    load_dotenv(dotenv_path=_ENV_PATH, override=True)


# Auto-load on import so any module that does `import env_loader` gets the vars
load_env()
