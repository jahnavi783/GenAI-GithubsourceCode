import importlib
import os


def test_job_status_lifecycle(tmp_path, monkeypatch):
    monkeypatch.setenv("DOCS_FOLDER", str(tmp_path))

    from agent import job_status

    importlib.reload(job_status)

    job_id = job_status.create_job("abc123", "dev")
    assert job_id

    created = job_status.get_job(job_id)
    assert created is not None
    assert created["status"] == "queued"

    updated = job_status.update_job(
        job_id,
        {
            "status": "running",
            "current_step": "fetch_diff",
            "steps_completed": ["fetch_diff"],
        },
    )

    assert updated is not None
    assert updated["status"] == "running"
    assert updated["current_step"] == "fetch_diff"

    final = job_status.update_job(
        job_id,
        {
            "status": "success",
            "docx_path": "generated_docs/commit_abc123_dev_20260301_000000.docx",
        },
    )

    assert final is not None
    assert final["status"] == "success"
    assert final["finished_at"] is not None

    jobs = job_status.list_jobs(limit=10)
    assert len(jobs) == 1
    assert jobs[0]["job_id"] == job_id

    status_file = os.path.join(str(tmp_path), ".pipeline_status.json")
    assert os.path.exists(status_file)
