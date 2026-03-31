"""
Section map — records which source files each doc section was generated from.

Format stored in generated_docs/.section_map_{owner}_{repo}.json:
{
  "repo_description": ["README.md", "package.json", ...],
  "architecture":     ["src/app.py", "src/main.py", ...],
  "api_section":      ["routes/users.py", "routes/auth.py", ...],
  "data_flow":        ["models/user.py", "db/schema.sql", ...]
}

The webhook pipeline reads this map to decide which sections to regenerate
when a commit changes specific files.
"""

import json
import os
from pathlib import Path

DOCS_FOLDER = os.getenv("DOCS_FOLDER", "./generated_docs")


def _map_path(owner: str, repo: str) -> str:
    safe = f"{owner}_{repo}".replace("/", "_").replace(" ", "_")
    return os.path.join(DOCS_FOLDER, f".section_map_{safe}.json")


def save_section_map(owner: str, repo: str, section_files: dict) -> None:
    """Persist the section → files mapping for a repo."""
    os.makedirs(DOCS_FOLDER, exist_ok=True)
    path = _map_path(owner, repo)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(section_files, f, indent=2)
    print(f"  Section map saved: {path}")


def load_section_map(owner: str, repo: str) -> dict:
    """Load the section → files mapping. Returns empty dict if not found."""
    path = _map_path(owner, repo)
    if not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def get_affected_sections(owner: str, repo: str, changed_files: list[str]) -> list[str]:
    """
    Given a list of files changed in a commit, return the doc sections
    that need to be regenerated.

    Falls back to regenerating ALL sections if no map exists yet.
    """
    section_map = load_section_map(owner, repo)
    if not section_map:
        # No map yet — regenerate everything
        return ["repo_description", "architecture", "api_section", "data_flow"]

    affected: set[str] = set()
    changed_set = set(changed_files)

    for section, source_files in section_map.items():
        if changed_set & set(source_files):
            affected.add(section)

    # Always regenerate commit_docs and impact_analysis (they're per-commit)
    affected.update(["commit_docs", "impact_analysis"])

    # If config / root files changed, refresh everything
    root_triggers = {
        "package.json", "requirements.txt", "pyproject.toml",
        "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
        "setup.py", "setup.cfg",
    }
    if changed_set & root_triggers:
        return ["repo_description", "architecture", "api_section", "data_flow", "commit_docs", "impact_analysis"]

    return sorted(affected)


def update_section_map(owner: str, repo: str, section: str, new_files: list[str]) -> None:
    """Update a single section's file list in the map."""
    section_map = load_section_map(owner, repo)
    section_map[section] = new_files
    save_section_map(owner, repo, section_map)
