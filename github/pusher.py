import base64
import os
import env_loader  # noqa: F401

import requests

from github.auth import get_installation_token


DOCS_FILENAME = "DOCUMENTATION.md"


def push_markdown_to_repo(content: str, commit_sha: str, branch: str,
                           owner: str = None, repo: str = None) -> str:
    """
    Creates or updates DOCUMENTATION.md in the root of the GitHub repo.
    owner/repo can be passed explicitly; falls back to env vars.
    Returns the URL of the committed file.
    """
    token = get_installation_token()
    owner = (owner or os.getenv("GITHUB_OWNER", "")).strip()
    repo  = (repo  or os.getenv("GITHUB_REPO",  "")).strip()
    if not owner or not repo:
        raise ValueError("GITHUB_OWNER and GITHUB_REPO must be configured")

    base = f"https://api.github.com/repos/{owner}/{repo}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Check if file already exists (need its SHA to update)
    existing_sha = None
    check_response = requests.get(
        f"{base}/contents/{DOCS_FILENAME}",
        headers=headers,
        params={"ref": branch},
    )
    if check_response.status_code == 200:
        existing_sha = check_response.json().get("sha")

    encoded_content = base64.b64encode(content.encode("utf-8")).decode("utf-8")

    payload = {
        "message": f"docs: auto-update DOCUMENTATION.md for commit {commit_sha[:7]}",
        "content": encoded_content,
        "branch":  branch,
    }
    if existing_sha:
        payload["sha"] = existing_sha

    put_response = requests.put(
        f"{base}/contents/{DOCS_FILENAME}",
        headers=headers,
        json=payload,
    )

    try:
        put_response.raise_for_status()
    except requests.HTTPError as error:
        raise RuntimeError(
            f"Failed to push DOCUMENTATION.md: HTTP {put_response.status_code} - {put_response.text}"
        ) from error

    html_url = (
        put_response.json()
        .get("content", {})
        .get("html_url", f"https://github.com/{owner}/{repo}/blob/{branch}/{DOCS_FILENAME}")
    )
    print(f"DOCUMENTATION.md pushed to repo: {html_url}")
    return html_url
