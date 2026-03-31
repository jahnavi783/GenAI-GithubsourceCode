import json
import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone

DOCS_FOLDER = os.getenv("DOCS_FOLDER", "./generated_docs")
STATUS_PATH = os.path.join(DOCS_FOLDER, ".pipeline_status.json")
LOCK_PATH = STATUS_PATH + ".lock"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def _lock_file():
    os.makedirs(DOCS_FOLDER, exist_ok=True)
    with open(LOCK_PATH, "a+", encoding="utf-8") as lock_handle:
        if os.name == "nt":
            import msvcrt

            lock_handle.seek(0)
            msvcrt.locking(lock_handle.fileno(), msvcrt.LK_LOCK, 1)
            try:
                yield
            finally:
                lock_handle.seek(0)
                msvcrt.locking(lock_handle.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_handle.fileno(), fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(lock_handle.fileno(), fcntl.LOCK_UN)


def _read_data() -> dict:
    if not os.path.exists(STATUS_PATH):
        return {"jobs": []}
    try:
        with open(STATUS_PATH, "r", encoding="utf-8") as handle:
            data = json.load(handle)
            if isinstance(data, dict) and isinstance(data.get("jobs"), list):
                return data
    except (json.JSONDecodeError, OSError):
        pass
    return {"jobs": []}


def _write_data(data: dict) -> None:
    os.makedirs(DOCS_FOLDER, exist_ok=True)
    with open(STATUS_PATH, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)


def create_job(commit_sha: str, branch: str) -> str:
    job_id = str(uuid.uuid4())
    now = _now_iso()
    job = {
        "job_id": job_id,
        "commit_sha": commit_sha,
        "branch": branch,
        "status": "queued",
        "current_step": None,
        "steps_completed": [],
        "error": None,
        "docx_path": None,
        "started_at": now,
        "updated_at": now,
        "finished_at": None,
    }
    with _lock_file():
        data = _read_data()
        data["jobs"].append(job)
        _write_data(data)
    return job_id


def update_job(job_id: str, fields: dict) -> dict | None:
    with _lock_file():
        data = _read_data()
        for job in data.get("jobs", []):
            if job.get("job_id") == job_id:
                job.update(fields)
                job["updated_at"] = _now_iso()
                if job.get("status") in {"success", "failed"} and not job.get("finished_at"):
                    job["finished_at"] = _now_iso()
                _write_data(data)
                return dict(job)
    return None


def get_job(job_id: str) -> dict | None:
    with _lock_file():
        data = _read_data()
        for job in data.get("jobs", []):
            if job.get("job_id") == job_id:
                return dict(job)
    return None


def list_jobs(limit: int = 100) -> list[dict]:
    with _lock_file():
        jobs = _read_data().get("jobs", [])
    jobs_sorted = sorted(jobs, key=lambda item: item.get("updated_at", ""), reverse=True)
    return jobs_sorted[:limit]
