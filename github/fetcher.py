import os
import env_loader  # noqa: F401
import base64

import requests

from github.auth import get_installation_token


# Files that give the most context about what the repo does
KEY_FILES = [
    "README.md", "readme.md", "README.rst",
    "requirements.txt", "package.json", "pyproject.toml",
    "setup.py", "setup.cfg", "Pipfile",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml",
    ".env.example", "config.yaml", "config.yml",
]

MAX_FILE_CHARS = 3000


def _get_base_and_headers(owner: str = None, repo: str = None):
    """
    Returns (base_url, headers_json, headers_diff) with a fresh token.
    owner/repo can be passed explicitly; falls back to env vars.
    """
    token = get_installation_token()
    owner = (owner or os.getenv("GITHUB_OWNER", "")).strip()
    repo  = (repo  or os.getenv("GITHUB_REPO",  "")).strip()

    if not owner or not repo:
        raise ValueError(
            "GITHUB_OWNER and GITHUB_REPO must be set (via args or .env)\n"
            f"  → Current values: OWNER='{owner}' REPO='{repo}'"
        )

    base = f"https://api.github.com/repos/{owner}/{repo}"
    headers_json = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    headers_diff = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3.diff",
    }
    return base, headers_json, headers_diff


def fetch_commit_diff(commit_sha: str, owner: str = None, repo: str = None) -> dict:
    owner = (owner or os.getenv("GITHUB_OWNER", "")).strip()
    repo  = (repo  or os.getenv("GITHUB_REPO",  "")).strip()
    base, headers_json, headers_diff = _get_base_and_headers(owner, repo)

    url = f"{base}/commits/{commit_sha}"
    print(f"  [fetch_diff] GET {url}")

    commit_response = requests.get(url, headers=headers_json, timeout=20)
    print(f"  [fetch_diff] Status: {commit_response.status_code}")

    if commit_response.status_code == 422:
        body = commit_response.text[:500]
        raise RuntimeError(
            f"GitHub returned 422 (Unprocessable) for commit {commit_sha[:7]}.\n"
            f"  → Owner: {owner}  Repo: {repo}\n"
            f"  → GitHub response: {body}"
        )
    if commit_response.status_code == 404:
        body = commit_response.text[:500]
        raise RuntimeError(
            f"Commit {commit_sha[:7]} not found (404).\n"
            f"  → Owner: {owner}  Repo: {repo}\n"
            f"  → Possible causes:\n"
            f"     1. The GitHub App is not installed on repo '{repo}'\n"
            f"     2. GITHUB_OWNER or GITHUB_REPO is wrong\n"
            f"  → GitHub response: {body}"
        )
    if commit_response.status_code == 401:
        raise RuntimeError(
            "401 Unauthorized fetching commit.\n"
            "  → Check GITHUB_APP_ID, GITHUB_INSTALLATION_ID, and private key."
        )

    commit_response.raise_for_status()

    diff_response = requests.get(url, headers=headers_diff, timeout=20)
    diff_response.raise_for_status()

    commit_payload = commit_response.json()
    commit_block   = commit_payload.get("commit", {})
    author_block   = commit_block.get("author", {})

    author_name   = author_block.get("name", "Unknown")
    message       = commit_block.get("message", "")
    timestamp     = author_block.get("date", "")
    files         = commit_payload.get("files", [])
    files_changed = [
        f["filename"] for f in files
        if isinstance(f, dict) and f.get("filename")
    ]

    print(f"  [fetch_diff] OK — author={author_name}, files={files_changed}")

    return {
        "sha":           commit_sha,
        "author":        author_name,
        "message":       message,
        "timestamp":     timestamp,
        "files_changed": files_changed,
        "diff":          diff_response.text,
    }


def fetch_repo_context(owner: str = None, repo: str = None) -> dict:
    base, headers_json, _ = _get_base_and_headers(owner, repo)

    tree_response = requests.get(
        f"{base}/git/trees/HEAD",
        headers=headers_json,
        params={"recursive": "1"},
        timeout=20,
    )
    tree_response.raise_for_status()
    tree_data = tree_response.json()

    file_tree = [
        item["path"]
        for item in tree_data.get("tree", [])
        if item.get("type") == "blob"
    ]

    key_file_contents = {}
    for filepath in file_tree:
        filename = os.path.basename(filepath)
        if filename in KEY_FILES and filepath not in key_file_contents:
            content = _fetch_file_content(base, filepath, headers_json)
            if content:
                key_file_contents[filepath] = content[:MAX_FILE_CHARS]

    return {
        "file_tree":         file_tree,
        "key_file_contents": key_file_contents,
    }


def _fetch_file_content(base_url: str, filepath: str, headers: dict) -> str:
    """Fetches raw content of a single file from the repo."""
    try:
        response = requests.get(
            f"{base_url}/contents/{filepath}",
            headers=headers,
            timeout=15,
        )
        if response.status_code != 200:
            return ""
        data = response.json()
        if data.get("encoding") == "base64":
            return base64.b64decode(data["content"]).decode("utf-8", errors="replace")
        return data.get("content", "")
    except Exception:
        return ""
