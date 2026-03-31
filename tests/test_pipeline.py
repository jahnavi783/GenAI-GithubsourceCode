from agent import pipeline


def test_pipeline_executes_in_strict_order(monkeypatch):
    calls = []


    def build_steps(_ctx):
        return {
            "fetch_diff": lambda: calls.append("fetch_diff"),
            "retrieve_context": lambda: calls.append("retrieve_context"),
            "generate_docs": lambda: calls.append("generate_docs"),
            "save_vectordb": lambda: calls.append("save_vectordb"),
            "save_docx": lambda: calls.append("save_docx"),
        }

    monkeypatch.setattr(pipeline, "make_steps", build_steps)

    result = pipeline.run_pipeline("abcdef123456", "dev")

    assert result["status"] == "success"
    assert calls == pipeline.PIPELINE_ORDER



def test_pipeline_fails_fast_on_step_error(monkeypatch):
    calls = []

    def explode():
        calls.append("generate_docs")
        raise ValueError("boom")

    def build_steps(_ctx):
        return {
            "fetch_diff": lambda: calls.append("fetch_diff"),
            "retrieve_context": lambda: calls.append("retrieve_context"),
            "generate_docs": explode,
            "save_vectordb": lambda: calls.append("save_vectordb"),
            "save_docx": lambda: calls.append("save_docx"),
        }

    monkeypatch.setattr(pipeline, "make_steps", build_steps)

    result = pipeline.run_pipeline("abcdef123456", "dev")

    assert result["status"] == "failed"
    assert "Step 'generate_docs' failed" in result["error"]
    assert result["steps_completed"] == ["fetch_diff", "retrieve_context"]
    assert "save_vectordb" not in calls



def test_regression_no_create_agent_usage():
    with open("agent/pipeline.py", "r", encoding="utf-8") as handle:
        source = handle.read()
    assert "create_agent" not in source
