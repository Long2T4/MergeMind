"""Stage 11: read-only GitHub client. GitHub is always mocked with httpx.MockTransport."""
import logging
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

import httpx
import pytest

from app.services import github_service
from app.services.github_service import (
    FileTooLarge, GitHubClient, GitHubNotConfigured, GitHubRateLimited, GitHubUnavailable,
    PullRequestNotFound, PullRequestRef, client_from_env, parse_pull_request_url,
)

TOKEN = "ghp_test_token_not_a_real_secret"
REF = PullRequestRef("octo-org", "sample-repo", 7)


def pr_body(**overrides):
    body = {
        "number": 7, "title": "Add parser", "html_url": "https://github.com/octo-org/sample-repo/pull/7",
        "user": {"login": "octo-student"}, "state": "open",
        "base": {"sha": "b" * 40, "repo": {"private": False, "full_name": "octo-org/sample-repo"}},
        "head": {"sha": "a" * 40}, "changed_files": 2, "additions": 10, "deletions": 3,
    }
    body.update(overrides)
    return body


def client_with(handler):
    return GitHubClient(TOKEN, transport=httpx.MockTransport(handler))


@pytest.mark.parametrize("url, expected", [
    ("https://github.com/octo-org/sample-repo/pull/7", PullRequestRef("octo-org", "sample-repo", 7)),
    ("  https://github.com/octo-org/sample.repo_2/pull/12/  ", PullRequestRef("octo-org", "sample.repo_2", 12)),
])
def test_parses_public_pull_request_urls(url, expected):
    assert parse_pull_request_url(url) == expected


@pytest.mark.parametrize("url", [
    "http://github.com/octo-org/sample-repo/pull/7",
    "https://www.github.com/octo-org/sample-repo/pull/7",
    "https://github.com.evil.example/octo-org/sample-repo/pull/7",
    "https://evil.example/github.com/octo-org/sample-repo/pull/7",
    "https://user@github.com/octo-org/sample-repo/pull/7",
    "https://github.com:8443/octo-org/sample-repo/pull/7",
    "https://github.com/octo-org/sample-repo/pull/7?x=1",
    "https://github.com/octo-org/sample-repo/pull/7#diff",
    "https://github.com/octo-org/sample-repo/pull/7/files",
    "https://github.com/octo-org/sample-repo/issues/7",
    "https://github.com/octo-org/sample-repo/pull/0",
    "https://github.com/octo-org/sample-repo/pull/-1",
    "https://github.com/octo-org/../pull/7",
    "https://github.com/octo-org/../../pull/7",
    "https://github.com/-bad/sample-repo/pull/7",
    "https://github.com/octo-org/sample%2Frepo/pull/7",
    "https://github.com/octo-org/sample-repo/pull/99999999999",
    "", "github.com/octo-org/sample-repo/pull/7", None, 7,
])
def test_rejects_anything_but_a_strict_pull_request_url(url):
    with pytest.raises(ValueError):
        parse_pull_request_url(url)


def test_fetches_pull_request_details_with_the_token_and_api_url_built_server_side():
    seen = []

    def handler(request):
        seen.append(request)
        return httpx.Response(200, json=pr_body())

    with client_with(handler) as client:
        details = client.get_pull_request(REF)
    assert str(seen[0].url) == "https://api.github.com/repos/octo-org/sample-repo/pulls/7"
    assert seen[0].headers["Authorization"] == f"Bearer {TOKEN}"
    assert details == {
        "owner": "octo-org", "repo": "sample-repo", "number": 7, "title": "Add parser",
        "author": "octo-student", "html_url": "https://github.com/octo-org/sample-repo/pull/7",
        "base_sha": "b" * 40, "head_sha": "a" * 40, "changed_files_count": 2,
        "additions": 10, "deletions": 3,
    }


def test_private_repositories_are_treated_as_not_found_even_when_the_token_can_read_them():
    with client_with(lambda request: httpx.Response(200, json=pr_body(
            base={"sha": "b" * 40, "repo": {"private": True}}))) as client:
        with pytest.raises(PullRequestNotFound, match="not found or not public"):
            client.get_pull_request(REF)


@pytest.mark.parametrize("response, error", [
    (httpx.Response(404, json={"message": "Not Found"}), PullRequestNotFound),
    (httpx.Response(401, json={"message": "Bad credentials"}), GitHubUnavailable),
    (httpx.Response(403, headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1900000000"},
                    json={"message": "API rate limit exceeded"}), GitHubRateLimited),
    (httpx.Response(429, headers={"retry-after": "60"}, json={"message": "slow down"}), GitHubRateLimited),
    (httpx.Response(403, json={"message": "You have exceeded a secondary rate limit"}), GitHubRateLimited),
    (httpx.Response(403, json={"message": "Resource not accessible"}), GitHubUnavailable),
    (httpx.Response(502, text="bad gateway"), GitHubUnavailable),
    (httpx.Response(200, text="not json"), GitHubUnavailable),
    (httpx.Response(200, json=["unexpected"]), GitHubUnavailable),
])
def test_maps_github_failures_to_clear_errors(response, error):
    with client_with(lambda request: response) as client:
        with pytest.raises(error):
            client.get_pull_request(REF)


def test_rate_limit_error_reports_when_the_limit_resets():
    response = httpx.Response(403, headers={"x-ratelimit-remaining": "0", "x-ratelimit-reset": "1900000000"},
                              json={"message": "API rate limit exceeded"})
    with client_with(lambda request: response) as client:
        with pytest.raises(GitHubRateLimited) as caught:
            client.get_pull_request(REF)
    assert "2030" in str(caught.value)


@pytest.mark.parametrize("failure", [httpx.ReadTimeout("slow"), httpx.ConnectError("down")])
def test_network_failures_become_unavailable(failure):
    def handler(request):
        raise failure

    with client_with(handler) as client:
        with pytest.raises(GitHubUnavailable):
            client.get_pull_request(REF)


def test_token_never_appears_in_errors_or_logs(caplog):
    caplog.set_level(logging.DEBUG)
    for status in (401, 403, 404, 500):
        with client_with(lambda request, status=status: httpx.Response(
                status, json={"message": f"echo {request.headers['Authorization']}"})) as client:
            with pytest.raises(Exception) as caught:
                client.get_pull_request(REF)
        assert TOKEN not in str(caught.value)
        assert TOKEN not in repr(caught.value)
    assert TOKEN not in caplog.text
    assert TOKEN not in repr(GitHubClient(TOKEN))


def test_lists_changed_files_across_pages():
    pages = {
        "1": [{"filename": f"src/f{n}.py", "status": "modified", "additions": 1, "deletions": 0,
               "patch": "@@ -1 +1 @@\n-a\n+b"} for n in range(100)],
        "2": [{"filename": "src/last.py", "status": "added", "additions": 2, "deletions": 0}],
    }

    def handler(request):
        assert request.url.path == "/repos/octo-org/sample-repo/pulls/7/files"
        assert request.url.params["per_page"] == "100"
        return httpx.Response(200, json=pages.get(request.url.params["page"], []))

    with client_with(handler) as client:
        files = client.list_files(REF)
    assert len(files) == 101
    assert files[0] == {"path": "src/f0.py", "status": "modified", "additions": 1, "deletions": 0,
                        "patch": "@@ -1 +1 @@\n-a\n+b"}
    assert files[-1]["patch"] is None


def test_reads_the_tree_and_file_contents_at_an_exact_commit():
    sha = "a" * 40

    def handler(request):
        if request.url.path == f"/repos/octo-org/sample-repo/git/trees/{sha}":
            assert request.url.params["recursive"] == "1"
            return httpx.Response(200, json={"truncated": False, "tree": [
                {"path": "src/app.py", "type": "blob", "size": 20},
                {"path": "src", "type": "tree"},
            ]})
        if request.url.raw_path.startswith(b"/repos/octo-org/sample-repo/contents/src/my%20app.py"):
            assert request.url.params["ref"] == sha
            assert request.headers["Accept"] == "application/vnd.github.raw+json"
            return httpx.Response(200, content="print('hi')\n".encode())
        if request.url.path.endswith("/contents/img.png"):
            return httpx.Response(200, content=b"\x89PNG\x00\xff")
        return httpx.Response(404, json={"message": "Not Found"})

    with client_with(handler) as client:
        assert client.get_tree(REF, sha) == {"src/app.py": 20}
        assert client.get_file_text(REF, "src/my app.py", sha) == "print('hi')\n"
        assert client.get_file_text(REF, "img.png", sha) is None
        assert client.get_file_text(REF, "missing.py", sha) is None


def test_file_downloads_stop_at_the_size_cap():
    with client_with(lambda request: httpx.Response(200, content=b"x = 1\n" * 2000)) as client:
        with pytest.raises(FileTooLarge):
            client.get_file_text(REF, "big.py", "a" * 40, max_chars=1000)
        assert client.get_file_text(REF, "big.py", "a" * 40, max_chars=20_000).startswith("x = 1")


def test_redirects_are_limited():
    with client_with(lambda request: httpx.Response(200, json={})) as client:
        assert client._client.max_redirects <= 3


def test_file_paths_from_github_cannot_escape_the_contents_endpoint():
    with client_with(lambda request: httpx.Response(200, text="x")) as client:
        for path in ("../secrets", "/etc/passwd", "a/../../b"):
            with pytest.raises(ValueError):
                client.get_file_text(REF, path, "a" * 40)


def test_client_requires_a_server_side_token(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(GitHubNotConfigured):
        client_from_env()
    monkeypatch.setenv("GITHUB_TOKEN", "   ")
    with pytest.raises(GitHubNotConfigured):
        client_from_env()
    monkeypatch.setenv("GITHUB_TOKEN", TOKEN)
    with client_from_env() as client:
        assert isinstance(client, GitHubClient)


def test_requests_have_a_timeout():
    assert 0 < github_service.REQUEST_TIMEOUT_SECONDS <= 30
