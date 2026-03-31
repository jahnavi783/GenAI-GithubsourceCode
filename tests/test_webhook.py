import hashlib
import hmac
import importlib

from fastapi.testclient import TestClient

import main


def _signature(payload: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode(), payload, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


def test_webhook_queues_all_push_commits(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
    importlib.reload(main)

    created_jobs = []
    calls = []

    def fake_create_job(commit_sha, branch):
        job_id = f"job-{len(created_jobs)+1}"
        created_jobs.append((job_id, commit_sha, branch))
        return job_id

    def fake_run_pipeline_job(job_id, commit_sha, branch):
        calls.append((job_id, commit_sha, branch))

    monkeypatch.setattr(main, "create_job", fake_create_job)
    monkeypatch.setattr(main, "run_pipeline_job", fake_run_pipeline_job)

    client = TestClient(main.app)
    payload = {
        "ref": "refs/heads/dev",
        "after": "aftersha",
        "commits": [{"id": "aaa111"}, {"id": "bbb222"}, {"id": "ccc333"}],
    }

    import json

    body = json.dumps(payload).encode("utf-8")
    response = client.post(
        "/webhook",
        content=body,
        headers={"X-Hub-Signature-256": _signature(body, "test-secret")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["branch"] == "dev"
    assert data["commit_count"] == 3
    assert data["commits"] == ["aaa111", "bbb222", "ccc333"]
    assert data["jobs"] == ["job-1", "job-2", "job-3"]
    assert calls == [
        ("job-1", "aaa111", "dev"),
        ("job-2", "bbb222", "dev"),
        ("job-3", "ccc333", "dev"),
    ]


def test_webhook_falls_back_to_after_when_commits_empty(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
    importlib.reload(main)

    created_jobs = []
    calls = []

    def fake_create_job(commit_sha, branch):
        job_id = f"job-{len(created_jobs)+1}"
        created_jobs.append((job_id, commit_sha, branch))
        return job_id

    def fake_run_pipeline_job(job_id, commit_sha, branch):
        calls.append((job_id, commit_sha, branch))

    monkeypatch.setattr(main, "create_job", fake_create_job)
    monkeypatch.setattr(main, "run_pipeline_job", fake_run_pipeline_job)

    client = TestClient(main.app)
    payload = {
        "ref": "refs/heads/dev",
        "after": "deadbeef",
        "commits": [],
    }

    import json

    body = json.dumps(payload).encode("utf-8")
    response = client.post(
        "/webhook",
        content=body,
        headers={"X-Hub-Signature-256": _signature(body, "test-secret")},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["commit_count"] == 1
    assert data["commits"] == ["deadbee"]
    assert data["jobs"] == ["job-1"]
    assert calls == [("job-1", "deadbeef", "dev")]


def test_jobs_endpoint_returns_store_contents(monkeypatch):
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "test-secret")
    importlib.reload(main)

    fake_jobs = [{"job_id": "job-1", "commit_sha": "abc", "status": "queued"}]
    monkeypatch.setattr(main, "list_jobs", lambda limit=100: fake_jobs[:limit])

    client = TestClient(main.app)
    response = client.get("/jobs")

    assert response.status_code == 200
    data = response.json()
    assert data["jobs"] == fake_jobs
    assert data["total"] == 1
