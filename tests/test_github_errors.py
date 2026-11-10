import sys
from unittest.mock import Mock

import pytest
from github import GithubException

from backend.agent import llm
from backend.core.errors import ReviewError
from backend.github_api import fetch


@pytest.mark.parametrize("payload,status", [
    ({"errors": [{"type": "NOT_FOUND"}]}, 404),
    ({"errors": [{"type": "RATE_LIMITED"}]}, 503),
    ({"errors": [{"message": "secret"}]}, 502),
    ({"data": {"user": None}}, 404),
    ({}, 502),
])
def test_graphql_failures(monkeypatch, payload, status):
    response = Mock()
    response.json.return_value = payload
    monkeypatch.setattr(fetch.requests, "post", Mock(return_value=response))
    with pytest.raises(ReviewError) as exc:
        fetch.get_pinned("example")
    assert exc.value.status_code == status
    assert "secret" not in str(exc.value)


def test_pinned_owner_is_case_insensitive(monkeypatch):
    response = Mock()
    response.json.return_value = {"data": {"user": {"pinnedItems": {"nodes": [
        {"name": "api", "url": "https://github.com/Example/api", "owner": {"login": "Example"}},
        {"name": "other", "url": "https://github.com/other/other", "owner": {"login": "other"}},
    ]}}}}
    monkeypatch.setattr(fetch.requests, "post", Mock(return_value=response))
    assert [r["name"] for r in fetch.get_pinned("example")] == ["api"]


@pytest.mark.parametrize("function,method,args,missing_status,expected", [
    (fetch.get_readme, "get_readme", (), 404, ""),
    (fetch.get_structure, "get_git_tree", (), 409, []),
    (fetch.get_commits, "get_commits", (), 409, []),
    (fetch.get_file, "get_contents", ("main.py",), 404, ""),
])
def test_missing_content_vs_service_failure(monkeypatch, function, method, args, missing_status, expected):
    gh = Mock()
    operation = getattr(gh.get_repo.return_value, method)
    monkeypatch.setattr(fetch, "gh", gh)
    operation.side_effect = GithubException(missing_status, {})
    assert function("example", "repo", *args) == expected
    operation.side_effect = GithubException(403, {})
    with pytest.raises(GithubException):
        function("example", "repo", *args)


def test_no_pins_falls_back_to_repositories(monkeypatch):
    monkeypatch.setattr(fetch, "get_pinned", Mock(return_value=[]))
    fallback = Mock(return_value=[{"name": "api", "url": "url"}])
    monkeypatch.setattr(fetch, "get_repos", fallback)
    monkeypatch.setattr(fetch, "get_readme", Mock(return_value="README"))
    monkeypatch.setattr(fetch, "get_structure", Mock(return_value=[]))
    monkeypatch.setattr(fetch, "get_commits", Mock(return_value=[]))
    assert fetch.fetch_profile("example")[0]["readme"] == "README"
    fallback.assert_called_once_with("example")


def test_missing_configuration(monkeypatch):
    config = sys.modules["backend.core.config"]
    monkeypatch.setattr(config, "GITHUB_TOKEN", None)
    monkeypatch.setattr(config, "GROQ_API_KEY", None)
    monkeypatch.setattr(fetch, "gh", None)
    monkeypatch.setattr(llm, "client", None)
    for call in (fetch.get_github, lambda: fetch.get_pinned("example"), lambda: llm.ask_llm("test")):
        with pytest.raises(ReviewError) as exc:
            call()
        assert exc.value.status_code == 503
