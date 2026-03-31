import pytest

from github import fetcher


class MockResponse:
    def __init__(self, status_code=200, json_data=None, text=""):
        self.status_code = status_code
        self._json = json_data if json_data is not None else {}
        self.text = text

    def raise_for_status(self):
        if self.status_code >= 400:
            raise fetcher.requests.HTTPError("http error")

    def json(self):
        return self._json


def test_fetch_commit_diff_http_failure(monkeypatch):
    monkeypatch.setattr(fetcher, "get_installation_token", lambda: "token")
    monkeypatch.setenv("GITHUB_OWNER", "o")
    monkeypatch.setenv("GITHUB_REPO", "r")

    def fake_get(*_args, **_kwargs):
        return MockResponse(status_code=404)

    monkeypatch.setattr(fetcher.requests, "get", fake_get)

    with pytest.raises(RuntimeError, match="Failed to fetch commit JSON"):
        fetcher.fetch_commit_diff("abc")


def test_fetch_commit_diff_missing_fields(monkeypatch):
    monkeypatch.setattr(fetcher, "get_installation_token", lambda: "token")
    monkeypatch.setenv("GITHUB_OWNER", "o")
    monkeypatch.setenv("GITHUB_REPO", "r")

    responses = [MockResponse(status_code=200, json_data={}), MockResponse(status_code=200, text="diff")]

    def fake_get(*_args, **_kwargs):
        return responses.pop(0)

    monkeypatch.setattr(fetcher.requests, "get", fake_get)

    with pytest.raises(ValueError, match="Missing 'commit'"):
        fetcher.fetch_commit_diff("abc")
