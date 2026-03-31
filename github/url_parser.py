"""
Parses a GitHub repository URL and extracts owner and repo name.
Supports formats:
  - https://github.com/owner/repo
  - https://github.com/owner/repo.git
  - git@github.com:owner/repo.git
"""
import re


def parse_github_url(url: str) -> tuple[str, str]:
    """
    Returns (owner, repo) from a GitHub URL.
    Raises ValueError if the URL cannot be parsed.
    """
    url = url.strip().rstrip("/")

    # HTTPS format: https://github.com/owner/repo or https://github.com/owner/repo.git
    https_match = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git)?$", url)
    if https_match:
        return https_match.group(1), https_match.group(2)

    # SSH format: git@github.com:owner/repo.git
    ssh_match = re.match(r"git@github\.com:([^/]+)/([^/]+?)(?:\.git)?$", url)
    if ssh_match:
        return ssh_match.group(1), ssh_match.group(2)

    raise ValueError(
        f"Could not parse GitHub URL: '{url}'\n"
        "Expected format: https://github.com/owner/repo"
    )
