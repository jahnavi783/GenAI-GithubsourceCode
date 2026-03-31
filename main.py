import hashlib
import hmac
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel

from agent.job_status import create_job, list_jobs, update_job
from agent.pipeline import run_pipeline

_ENV_PATH = Path(__file__).resolve().parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH, override=True)

app = FastAPI(title="Git Doc Agent", version="3.0.0")

DOCS_FOLDER = os.getenv("DOCS_FOLDER", "./generated_docs")
os.makedirs(DOCS_FOLDER, exist_ok=True)


def _webhook_debug() -> bool:
    return os.getenv("WEBHOOK_DEBUG", "true").lower() in {"1", "true", "yes", "on"}


def verify_signature(payload: bytes, signature: str) -> tuple[bool, str]:
    secret_value = os.getenv("GITHUB_WEBHOOK_SECRET", "").strip()
    if not secret_value:
        try:
            load_dotenv(dotenv_path=_ENV_PATH, override=True)
            secret_value = os.getenv("GITHUB_WEBHOOK_SECRET", "").strip()
        except Exception:
            pass
    if not secret_value:
        return False, "GITHUB_WEBHOOK_SECRET is empty — check your .env file"
    if not signature:
        return False, "X-Hub-Signature-256 header is missing"
    if not signature.startswith("sha256="):
        return False, "X-Hub-Signature-256 header has invalid format"
    secret = secret_value.encode()
    expected = "sha256=" + hmac.new(secret, payload, hashlib.sha256).hexdigest()
    if hmac.compare_digest(expected, signature):
        return True, "signature matched"
    return False, f"signature mismatch (expected prefix={expected[:16]}, received prefix={signature[:16]})"


def run_pipeline_job(job_id: str, commit_sha: str, branch: str, owner: str = None, repo: str = None) -> None:
    def step_update(fields: dict):
        update_job(job_id, fields)

    update_job(job_id, {"status": "running", "current_step": None, "steps_completed": [], "error": None})
    result = run_pipeline(commit_sha, branch, owner=owner, repo=repo, on_step_update=step_update)
    update_job(job_id, {
        "status": result.get("status", "failed"),
        "current_step": result.get("current_step"),
        "steps_completed": result.get("steps_completed", []),
        "docx_path": result.get("docx_path"),
        "markdown_url": result.get("markdown_url"),
        "error": result.get("error"),
    })


def run_initial_pipeline_job(job_id: str, owner: str, repo: str, branch: str) -> None:
    from agent.initial_pipeline import run_initial_pipeline

    def step_update(fields: dict):
        update_job(job_id, fields)

    update_job(job_id, {"status": "running", "current_step": None, "steps_completed": [], "error": None})
    result = run_initial_pipeline(owner, repo, branch, on_step_update=step_update)
    update_job(job_id, {
        "status": result.get("status", "failed"),
        "current_step": result.get("current_step"),
        "steps_completed": result.get("steps_completed", []),
        "docx_path": result.get("docx_path"),
        "markdown_url": result.get("markdown_url"),
        "error": result.get("error"),
    })


# ── Routes ────────────────────────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    github_url: str
    branch: str = "main"


@app.post("/generate")
async def generate_from_url(body: GenerateRequest, bg: BackgroundTasks):
    """
    Accepts a GitHub repo URL and generates a full system design document.
    This is the FIRST-TIME endpoint — paste a URL and get a full doc.

    Example body:
        { "github_url": "https://github.com/owner/repo", "branch": "main" }
    """
    from github.url_parser import parse_github_url
    try:
        owner, repo = parse_github_url(body.github_url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    job_id = create_job(f"initial:{owner}/{repo}", body.branch)
    bg.add_task(run_initial_pipeline_job, job_id, owner, repo, body.branch)

    return {
        "status": "processing",
        "message": f"Generating full design document for {owner}/{repo} on branch '{body.branch}'",
        "owner": owner,
        "repo": repo,
        "branch": body.branch,
        "job_id": job_id,
        "track_progress": f"/jobs/{job_id}",
    }


@app.post("/webhook")
async def receive_webhook(request: Request, bg: BackgroundTasks):
    payload_bytes = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")

    is_valid, reason = verify_signature(payload_bytes, signature)
    if not is_valid:
        if _webhook_debug():
            print(f"Webhook signature validation failed: {reason}")
        raise HTTPException(status_code=401, detail="Invalid signature")

    payload = await request.json()
    if "commits" not in payload:
        return {"status": "ignored - not a push event"}

    branch = payload.get("ref", "").replace("refs/heads/", "")
    commit_shas = [
        item.get("id")
        for item in payload.get("commits", [])
        if isinstance(item, dict) and item.get("id")
    ]
    if not commit_shas:
        after_sha = payload.get("after")
        if after_sha:
            commit_shas = [after_sha]

    if not commit_shas:
        return {"status": "ignored - no commit SHAs found", "branch": branch, "commits": [], "jobs": []}

    commit_shas = [sha for sha in commit_shas if sha]
    short_commits = [sha[:7] for sha in commit_shas]
    print(f"\nWebhook received - {len(commit_shas)} commit(s) on {branch}: {short_commits}")

    # Extract repo owner/name from webhook payload (works for any repo)
    repo_full = payload.get("repository", {}).get("full_name", "")
    if "/" in repo_full:
        webhook_owner, webhook_repo = repo_full.split("/", 1)
    else:
        webhook_owner = os.getenv("GITHUB_OWNER", "")
        webhook_repo  = os.getenv("GITHUB_REPO", "")

    print(f"Webhook repo: {webhook_owner}/{webhook_repo}")

    job_ids: list[str] = []
    for commit_sha in commit_shas:
        if isinstance(commit_sha, str):
            job_id = create_job(commit_sha, branch)
            job_ids.append(job_id)
            bg.add_task(run_pipeline_job, job_id, commit_sha, branch, webhook_owner, webhook_repo)

    return {
        "status": "processing",
        "repo": f"{webhook_owner}/{webhook_repo}",
        "branch": branch,
        "commit_count": len(commit_shas),
        "commits": short_commits,
        "jobs": job_ids,
    }


@app.get("/jobs")
def get_jobs(limit: int = 100):
    return {"total": len(list_jobs(limit=1000000)), "jobs": list_jobs(limit=limit)}


@app.get("/jobs/{job_id}")
def get_job_by_id(job_id: str):
    from agent.job_status import get_job
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@app.get("/docs-list")
def list_docs():
    files = [f for f in os.listdir(DOCS_FOLDER) if f.endswith(".docx")]
    return {"total": len(files), "files": sorted(files, reverse=True)}


@app.get("/docs/download/{filename}")
def download_doc(filename: str):
    filepath = os.path.join(DOCS_FOLDER, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(
        path=filepath,
        filename=filename,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )


@app.get("/health")
def health():
    load_dotenv(dotenv_path=_ENV_PATH, override=True)
    secret_loaded = bool(os.getenv("GITHUB_WEBHOOK_SECRET", "").strip())
    return {
        "status": "running",
        "version": "3.0.0",
        "model": os.getenv("LLM_MODEL"),
        "repo": os.getenv("GITHUB_REPO"),
        "webhook_secret_loaded": secret_loaded,
        "env_path": str(_ENV_PATH),
        "env_exists": _ENV_PATH.exists(),
    }


@app.get("/debug/env")
def debug_env():
    load_dotenv(dotenv_path=_ENV_PATH, override=True)

    def _status(key: str, secret: bool = False) -> dict:
        val = os.getenv(key, "").strip()
        return {"loaded": bool(val), "value": ("***" if secret else val) if val else "MISSING ❌"}

    return {
        "env_file": {"path": str(_ENV_PATH), "exists": _ENV_PATH.exists()},
        "github_app": {
            "GITHUB_APP_ID":           _status("GITHUB_APP_ID"),
            "GITHUB_INSTALLATION_ID":  _status("GITHUB_INSTALLATION_ID"),
            "GITHUB_OWNER":            _status("GITHUB_OWNER"),
            "GITHUB_REPO":             _status("GITHUB_REPO"),
            "GITHUB_PRIVATE_KEY_PATH": _status("GITHUB_PRIVATE_KEY_PATH"),
            "GITHUB_WEBHOOK_SECRET":   _status("GITHUB_WEBHOOK_SECRET", secret=True),
        },
        "llm": {
            "OLLAMA_BASE_URL": _status("OLLAMA_BASE_URL"),
            "LLM_MODEL":       _status("LLM_MODEL"),
            "EMBED_MODEL":     _status("EMBED_MODEL"),
        },
        "storage": {
            "CHROMA_PATH": _status("CHROMA_PATH"),
            "DOCS_FOLDER": _status("DOCS_FOLDER"),
        },
    }


@app.get("/debug/test-commit/{sha}")
def debug_test_commit(sha: str):
    import requests as req
    from github.auth import get_installation_token
    load_dotenv(dotenv_path=_ENV_PATH, override=True)
    owner = os.getenv("GITHUB_OWNER", "").strip()
    repo  = os.getenv("GITHUB_REPO", "").strip()
    try:
        token = get_installation_token()
    except Exception as e:
        return {"status": "error", "step": "auth", "error": str(e)}
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}"
    resp = req.get(url, headers={"Authorization": f"token {token}", "Accept": "application/vnd.github.v3+json"}, timeout=10)
    return {
        "url": url, "status": resp.status_code, "ok": resp.status_code == 200,
        "body_preview": resp.text[:400],
        "tip": "200 = working ✅ | 404 = wrong owner/repo | 422 = SHA malformed | 401 = bad token",
    }
