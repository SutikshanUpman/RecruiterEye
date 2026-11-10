from types import SimpleNamespace
from unittest.mock import Mock

import groq
import httpx
import pytest
import requests
from fastapi.testclient import TestClient
from github import GithubException

from backend.agent import keywords, llm, reviewer, scorer
from backend.agent.filter import filter_repos
from backend.core.errors import ReviewError
from backend.main import app
from backend.routers import review

client = TestClient(app)
PAYLOAD = {"username": "example", "job_input": "Backend developer"}
SCORES = '{"commit_history": 7, "structure": 8, "readme": 9}'


def repo(name="python-api"):
    return dict(name=name, url=f"https://github.com/example/{name}",
                readme="python fastapi", structure=["main.py"], commits=[])


@pytest.mark.parametrize("count", [1, 3, 6])
def test_full_pipeline(monkeypatch, count):
    fetch_mock = Mock(return_value=[repo(f"python-{i}") for i in range(count)])
    monkeypatch.setattr(review, "fetch_profile", fetch_mock)
    keyword_llm = Mock(return_value="python, fastapi")
    score_llm = Mock(return_value=SCORES)
    review_llm = Mock(return_value="Specific review")
    monkeypatch.setattr(keywords, "ask_llm", keyword_llm)
    monkeypatch.setattr(scorer, "ask_llm", score_llm)
    monkeypatch.setattr(reviewer, "ask_llm", review_llm)
    monkeypatch.setattr(reviewer, "get_file", Mock(return_value="print('hello')"))
    response = client.post("/review", json={"username": " example ", "job_input": " Backend developer "})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["repos_fetched"] == count
    assert body["repos_scored"] == min(count, 4)
    assert len(body["reviews"]) == min(count, 2)
    assert score_llm.call_count == min(count, 4)
    assert review_llm.call_count == min(count, 2)
    assert all(r["total"] == 24 for r in body["reviews"])
    assert all("Job description or role: Backend developer" in c.args[0] for c in review_llm.call_args_list)
    fetch_mock.assert_called_once_with("example")


def test_empty_profile_avoids_llm(monkeypatch):
    monkeypatch.setattr(review, "fetch_profile", Mock(return_value=[]))
    keyword_mock = Mock(side_effect=AssertionError("Should not call LLM"))
    monkeypatch.setattr(review, "get_keywords", keyword_mock)
    response = client.post("/review", json=PAYLOAD)
    assert response.status_code == 200
    assert response.json() == dict(username="example", keywords=[], repos_fetched=0, repos_scored=0, reviews=[])


@pytest.mark.parametrize("field,value", [("username", "bad/user"), ("username", "-abc"), ("username", "a" * 40), ("job_input", "  "), ("job_input", "a" * 3001), ("job_input", None)])
def test_invalid_input(monkeypatch, field, value):
    fetch_mock = Mock()
    monkeypatch.setattr(review, "fetch_profile", fetch_mock)
    assert client.post("/review", json={**PAYLOAD, field: value}).status_code == 422
    fetch_mock.assert_not_called()


@pytest.mark.parametrize("error,status", [
    (GithubException(404, {"message": "secret"}), 404),
    (GithubException(403, {"message": "secret"}), 503),
    (GithubException(500, {"message": "secret"}), 502),
    (requests.Timeout("secret"), 504),
    (requests.ConnectionError("secret"), 502),
    (groq.APITimeoutError(request=httpx.Request("POST", "https://example.com")), 504),
    (groq.APIConnectionError(request=httpx.Request("POST", "https://example.com")), 502),
    (groq.RateLimitError("secret", response=httpx.Response(429, request=httpx.Request("POST", "https://example.com")), body=None), 503),
])
def test_upstream_errors_are_safe(monkeypatch, error, status):
    monkeypatch.setattr(review, "fetch_profile", Mock(side_effect=error))
    response = client.post("/review", json=PAYLOAD)
    assert response.status_code == status
    assert "secret" not in response.text


@pytest.mark.parametrize("reply", ["not json", "{}", '[]', '{"commit_history": true, "structure": 8, "readme": 9}', '{"commit_history": 11, "structure": 8, "readme": 9}', '{"commit_history": "7", "structure": 8, "readme": 9}', '{"commit_history": 7, "structure": 8, "readme": 9, "extra": 10}'])
def test_invalid_scores_fail_request(monkeypatch, reply):
    monkeypatch.setattr(review, "fetch_profile", Mock(return_value=[repo()]))
    monkeypatch.setattr(keywords, "ask_llm", Mock(return_value="python"))
    monkeypatch.setattr(scorer, "ask_llm", Mock(return_value=reply))
    response = client.post("/review", json=PAYLOAD)
    assert response.status_code == 502
    assert "invalid repository scores" in response.json()["detail"]


@pytest.mark.parametrize("content", [None, "", "   "])
def test_empty_model_response(monkeypatch, content):
    fake = Mock()
    fake.chat.completions.create.return_value = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])
    monkeypatch.setattr(llm, "client", fake)
    with pytest.raises(ReviewError, match="empty response"):
        llm.ask_llm("test")


def test_invalid_keywords(monkeypatch):
    monkeypatch.setattr(keywords, "ask_llm", Mock(return_value=", ,"))
    with pytest.raises(ReviewError, match="invalid skill keywords"):
        keywords.get_keywords("developer")


def test_missing_code_is_not_presented_as_code(monkeypatch):
    monkeypatch.setattr(reviewer, "get_file", Mock(return_value=""))
    ask = Mock(return_value="Review")
    monkeypatch.setattr(reviewer, "ask_llm", ask)
    reviewer.review_repo("example", repo(), "developer")
    assert "Code:\n(none)" in ask.call_args.args[0]


def test_empty_vocabulary():
    result = filter_repos([dict(name="a", readme="the", structure=[])], ["and"])
    assert result[0]["relevance"] == 0


def test_health_and_docs():
    assert client.get("/health").json() == {"status": "ok"}
    assert "/review" in client.get("/openapi.json").json()["paths"]
