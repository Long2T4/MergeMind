from datetime import datetime

from pydantic import BaseModel, Field, StrictStr, model_validator


class UserCreate(BaseModel):
    name: str
    email: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    user_id: int
    name: str
    description: str | None = None


class ProjectOut(BaseModel):
    id: int
    user_id: int
    name: str
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class ProjectContextInput(BaseModel):
    file_path: str = Field(min_length=1, max_length=240)
    source_root: str = Field(default="", max_length=240)
    files: dict[StrictStr, StrictStr] = Field(max_length=50)

    @model_validator(mode="after")
    def limit_snapshot(self):
        if any(len(path) > 240 for path in self.files):
            raise ValueError("Project paths must be at most 240 characters")
        if sum(len(content) for content in self.files.values()) > 200_000:
            raise ValueError("Project snapshot must be at most 200000 characters")
        return self


class ContextSummary(BaseModel):
    file_path: str
    selected_files: list[str]
    total_chars: int
    unresolved_imports: list[str]
    omitted_files: list[str]


class CodeReviewCreate(BaseModel):
    project_id: int
    submitted_code: str = Field(max_length=200_000)
    programming_language: str = Field(min_length=1, max_length=40)
    project_context: ProjectContextInput | None = None


class ReviewIssueOut(BaseModel):
    id: int
    review_id: int
    title: str | None
    category: str
    severity: str
    file_name: str | None
    line_number: int | None
    explanation: str
    why_it_matters: str | None
    suggested_fix: str | None
    confidence_score: int | None = None
    confidence_level: str | None = None
    confidence_evidence: dict | None = None
    status: str
    # Stage 12: who last changed the status (a user id), and when. Empty until changed.
    status_updated_at: datetime | None = None
    status_updated_by: int | None = None
    # Stage 11: True when a pull request finding is not on a changed line.
    outside_diff: bool | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class PullRequestReviewCreate(BaseModel):
    project_id: int
    pr_url: str = Field(min_length=1, max_length=300)
    # Python import root inside the repository, for example "backend".
    source_root: str = Field(default="", max_length=240)


class PullRequestFileOut(BaseModel):
    id: int
    path: str
    status: str
    additions: int
    deletions: int
    patch: str | None
    language: str | None
    review_state: str
    skip_reason: str | None

    class Config:
        from_attributes = True


class PullRequestOut(BaseModel):
    id: int
    owner: str
    repo: str
    number: int
    title: str
    author: str
    html_url: str
    base_sha: str
    head_sha: str
    source_root: str
    changed_files_count: int
    additions: int
    deletions: int
    created_at: datetime
    files: list[PullRequestFileOut] = Field(default_factory=list)

    class Config:
        from_attributes = True


class CodeReviewOut(BaseModel):
    id: int
    project_id: int
    submitted_code: str
    programming_language: str
    review_status: str
    created_at: datetime
    risk_score: int | None = None
    risk_level: str | None = None
    risk_breakdown: dict | None = None
    issues: list[ReviewIssueOut] = Field(default_factory=list)
    # Only the POST response includes context diagnostics; snapshots are not stored.
    context_summary: ContextSummary | None = None
    # Stage 11: set only for pull request reviews.
    pull_request_id: int | None = None
    pull_request: PullRequestOut | None = None

    class Config:
        from_attributes = True
