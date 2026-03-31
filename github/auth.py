import os
import env_loader  # noqa: F401 — loads .env with absolute path
import time

import jwt
import requests


def get_installation_token() -> str:
    """
    Generates a GitHub App installation token.

    Required .env variables:
        GITHUB_APP_ID             — e.g. 123456
        GITHUB_PRIVATE_KEY_PATH   — absolute path to the .pem file
        GITHUB_INSTALLATION_ID    — e.g. 112854524
    """
    # ── Validate all required vars upfront with clear messages ────────────
    app_id = os.getenv("GITHUB_APP_ID", "").strip()
    key_path = os.getenv("GITHUB_PRIVATE_KEY_PATH", "").strip()
    installation_id = os.getenv("GITHUB_INSTALLATION_ID", "").strip()

    missing = []
    if not app_id:
        missing.append("GITHUB_APP_ID")
    if not key_path:
        missing.append("GITHUB_PRIVATE_KEY_PATH")
    if not installation_id:
        missing.append("GITHUB_INSTALLATION_ID")

    if missing:
        raise ValueError(
            f"Missing required GitHub App env vars: {', '.join(missing)}\n"
            f"  → Check your .env file at: {os.getenv('ENV_PATH', '.env')}\n"
            f"  → GITHUB_APP_ID is found on: GitHub → Settings → Developer Settings → GitHub Apps → your app"
        )

    # ── Read private key ──────────────────────────────────────────────────
    try:
        with open(key_path, encoding="utf-8") as key_file:
            private_key = key_file.read()
    except FileNotFoundError:
        raise FileNotFoundError(
            f"GitHub private key not found at: {key_path}\n"
            f"  → Download it from: GitHub → Settings → Developer Settings → GitHub Apps → your app → Private keys"
        )

    # ── Build JWT ─────────────────────────────────────────────────────────
    now = int(time.time())
    jwt_payload = {
        "iat": now - 60,   # issued 60s ago to avoid clock skew
        "exp": now + 540,  # 9 minute expiry (max is 10)
        "iss": app_id,
    }
    jwt_token = jwt.encode(jwt_payload, private_key, algorithm="RS256")

    # ── Exchange JWT for installation access token ────────────────────────
    url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"
    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github.v3+json",
        },
        timeout=15,
    )

    if response.status_code == 401:
        raise RuntimeError(
            f"GitHub App authentication failed (401).\n"
            f"  → Verify GITHUB_APP_ID={app_id} is correct\n"
            f"  → Verify the private key at {key_path} belongs to this app\n"
            f"  → Re-download a fresh .pem from GitHub if needed"
        )
    if response.status_code == 404:
        raise RuntimeError(
            f"Installation ID not found (404).\n"
            f"  → Verify GITHUB_INSTALLATION_ID={installation_id} is correct\n"
            f"  → Go to: GitHub → Settings → Developer Settings → GitHub Apps → your app → Install App"
        )

    try:
        response.raise_for_status()
    except requests.HTTPError as error:
        raise RuntimeError(
            f"Failed to get GitHub installation token: HTTP {response.status_code}\n"
            f"  → Response: {response.text[:300]}"
        ) from error

    token = response.json().get("token")
    if not token:
        raise RuntimeError(
            f"GitHub installation token missing in API response.\n"
            f"  → Full response: {response.text[:300]}"
        )
    return token
