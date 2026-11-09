"""Stage 11: read-only GitHub REST client for public pull requests.

The user's URL is only parsed, never requested: API addresses are built here
from validated owner, repository and number values. The token is read from
the server environment and is never logged, returned or put in an error.
"""
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import quote

import httpx

from app.services.project_context_service import _project_path

API_BASE_URL = "https://api.github.com"
REQUEST_TIMEOUT_SECONDS = 20
FILES_PER_PAGE = 100
# GitHub lists at most 3,000 files for a pull request.
MAX_FILE_PAGES = 30
MAX_PR_NUMBER = 2_147_483_647  # fits the database integer column

PR_URL_PATTERN = re.compile(
    r"https://github\.com/"
    r"(?P<owner>[A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/"
    r"(?P<repo>[A-Za-z0-9._-]{1,100})/"
    r"pull/(?P<number>[1-9][0-9]{0,9})/?"
)


class GitHubError(Exception):
    """A GitHub failure with a message that is safe to show to users."""
    status_code = 502


class PullRequestNotFound(GitHubError):
    status_code = 404


class GitHubRateLimited(GitHubError):
    status_code = 503


class GitHubUnavailable(GitHubError):
    status_code = 503


class GitHubNotConfigured(GitHubError):
    status_code = 503


class FileTooLarge(ValueError):
    """A file was bigger than the caller's limit; the download stopped early."""


NOT_FOUND_MESSAGE = "Pull request not found or not public. MergeMind can only review public repositories."
UNEXPECTED_MESSAGE = "GitHub returned an unexpected response."


@dataclass(frozen=True)
class PullRequestRef:
    owner: str
    repo: str
    number: int


def parse_pull_request_url(url) -> PullRequestRef:
    """Accept only https://github.com/{owner}/{repo}/pull/{number}."""
    if not isinstance(url, str):
        raise ValueError("Enter a GitHub pull request URL")
    match = PR_URL_PATTERN.fullmatch(url.strip())
    if not match or match["repo"] in {".", ".."}:
        raise ValueError(
            "Enter a pull request URL like https://github.com/owner/repository/pull/123"
        )
    number = int(match["number"])
    if number > MAX_PR_NUMBER:
        raise ValueError("The pull request number is too large")
    return PullRequestRef(match["owner"], match["repo"], number)


def _rate_limit_error(response: httpx.Response) -> GitHubRateLimited | None:
    remaining = response.headers.get("x-ratelimit-remaining")
    retry_after = response.headers.get("retry-after")
    try:
        message = str(response.json().get("message", ""))
    except (ValueError, AttributeError):
        message = ""
    limited = (
        response.status_code == 429 or remaining == "0" or retry_after is not None
        or "rate limit" in message.lower()
    )
    if not limited:
        return None
    reset = response.headers.get("x-ratelimit-reset", "")
    if reset.isdigit():
        when = datetime.fromtimestamp(int(reset), tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        return GitHubRateLimited(f"GitHub's rate limit was reached. Try again after {when}.")
    if retry_after and retry_after.isdigit():
        return GitHubRateLimited(f"GitHub's rate limit was reached. Try again in {retry_after} seconds.")
    return GitHubRateLimited("GitHub's rate limit was reached. Try again in a few minutes.")


class GitHubClient:
    def __init__(self, token: str, *, transport: httpx.BaseTransport | None = None):
        self._client = httpx.Client(
            base_url=API_BASE_URL,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "MergeMind-code-review",
            },
            timeout=REQUEST_TIMEOUT_SECONDS,
            # httpx drops the Authorization header on a redirect to another host.
            follow_redirects=True,
            # Only needed for renamed repositories.
            max_redirects=3,
            transport=transport,
        )

    def __repr__(self) -> str:
        return "GitHubClient()"

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        self.close()

    def close(self) -> None:
        self._client.close()

    @staticmethod
    def _read_capped(response: httpx.Response, max_bytes: int | None) -> bytes:
        # Stream so an oversized file is never held in memory whole.
        body = bytearray()
        for chunk in response.iter_bytes():
            body.extend(chunk)
            if max_bytes is not None and len(body) > max_bytes:
                raise FileTooLarge("File is larger than the review limit")
        return bytes(body)

    def _get(self, path: str, *, params=None, raw: bool = False, missing_ok: bool = False,
             max_bytes: int | None = None):
        headers = {"Accept": "application/vnd.github.raw+json"} if raw else None
        try:
            with self._client.stream("GET", path, params=params, headers=headers) as response:
                if raw and response.status_code == 200:
                    return self._read_capped(response, max_bytes)
                response.read()
        except httpx.TimeoutException:
            raise GitHubUnavailable("GitHub did not respond in time. Try again shortly.") from None
        except httpx.HTTPError:
            raise GitHubUnavailable("Could not reach GitHub. Try again shortly.") from None

        if response.status_code == 404:
            if missing_ok:
                return None
            raise PullRequestNotFound(NOT_FOUND_MESSAGE)
        if response.status_code in (403, 429):
            limited = _rate_limit_error(response)
            if limited:
                raise limited
            raise GitHubUnavailable("GitHub refused the request. Check the server's GitHub token.")
        if response.status_code == 401:
            raise GitHubUnavailable("GitHub rejected the server's token. Ask the administrator to update GITHUB_TOKEN.")
        if response.status_code != 200:
            raise GitHubUnavailable(f"GitHub returned an error (status {response.status_code}). Try again shortly.")
        try:
            return response.json()
        except ValueError:
            raise GitHubUnavailable(UNEXPECTED_MESSAGE) from None

    @staticmethod
    def _repo_path(ref: PullRequestRef) -> str:
        return f"/repos/{ref.owner}/{ref.repo}"

    def get_pull_request(self, ref: PullRequestRef) -> dict:
        data = self._get(f"{self._repo_path(ref)}/pulls/{ref.number}")
        try:
            if data["base"]["repo"]["private"] is not False:
                raise PullRequestNotFound(NOT_FOUND_MESSAGE)
            return {
                "owner": ref.owner,
                "repo": ref.repo,
                "number": ref.number,
                "title": str(data["title"])[:500],
                "author": str((data.get("user") or {}).get("login") or "unknown")[:255],
                "html_url": f"https://github.com/{ref.owner}/{ref.repo}/pull/{ref.number}",
                "base_sha": str(data["base"]["sha"])[:64],
                "head_sha": str(data["head"]["sha"])[:64],
                "changed_files_count": int(data["changed_files"]),
                "additions": int(data["additions"]),
                "deletions": int(data["deletions"]),
            }
        except (KeyError, TypeError, ValueError):
            raise GitHubUnavailable(UNEXPECTED_MESSAGE) from None

    def list_files(self, ref: PullRequestRef) -> list[dict]:
        files = []
        for page in range(1, MAX_FILE_PAGES + 1):
            batch = self._get(
                f"{self._repo_path(ref)}/pulls/{ref.number}/files",
                params={"per_page": FILES_PER_PAGE, "page": page},
            )
            if not isinstance(batch, list):
                raise GitHubUnavailable(UNEXPECTED_MESSAGE)
            try:
                files.extend({
                    "path": str(item["filename"]),
                    "status": str(item["status"]),
                    "additions": int(item.get("additions") or 0),
                    "deletions": int(item.get("deletions") or 0),
                    "patch": item["patch"] if isinstance(item.get("patch"), str) else None,
                } for item in batch)
            except (KeyError, TypeError, ValueError, AttributeError):
                raise GitHubUnavailable(UNEXPECTED_MESSAGE) from None
            if len(batch) < FILES_PER_PAGE:
                break
        return files

    def get_tree(self, ref: PullRequestRef, sha: str) -> dict[str, int]:
        """Paths and sizes of every file at a commit (may be truncated for huge repositories)."""
        data = self._get(f"{self._repo_path(ref)}/git/trees/{quote(sha, safe='')}", params={"recursive": "1"})
        entries = data.get("tree") if isinstance(data, dict) else None
        if not isinstance(entries, list):
            raise GitHubUnavailable(UNEXPECTED_MESSAGE)
        tree = {}
        for entry in entries:
            if isinstance(entry, dict) and entry.get("type") == "blob" and isinstance(entry.get("path"), str):
                size = entry.get("size")
                tree[entry["path"]] = size if isinstance(size, int) else 0
        return tree

    def get_file_text(self, ref: PullRequestRef, path: str, sha: str, *, max_chars: int | None = None) -> str | None:
        """A file's text at a commit; None if it is missing or not UTF-8 text.
        Raises FileTooLarge, without downloading the rest, past max_chars."""
        safe_path = _project_path(path)  # rejects absolute paths and ".."
        content = self._get(
            f"{self._repo_path(ref)}/contents/{quote(safe_path, safe='/')}",
            params={"ref": sha}, raw=True, missing_ok=True,
            # A UTF-8 character is at most 4 bytes.
            max_bytes=max_chars * 4 if max_chars is not None else None,
        )
        if content is None:
            return None
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            return None
        if max_chars is not None and len(text) > max_chars:
            raise FileTooLarge("File is larger than the review limit")
        return None if "\x00" in text else text


def get_github_client_factory():
    """FastAPI dependency: how routes and background tasks open a client.
    Tests replace it with a client backed by a fake GitHub."""
    return client_from_env


def client_from_env() -> GitHubClient:
    token = (os.getenv("GITHUB_TOKEN") or "").strip()
    if not token:
        raise GitHubNotConfigured(
            "GitHub pull request reviews aren't configured on this server (GITHUB_TOKEN is not set)."
        )
    return GitHubClient(token)
