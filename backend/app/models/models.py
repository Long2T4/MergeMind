from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Integer, String, Text, DateTime, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    projects: Mapped[list["Project"]] = relationship(back_populates="user")


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped["User"] = relationship(back_populates="projects")
    code_reviews: Mapped[list["CodeReview"]] = relationship(back_populates="project")


class CodeReview(Base):
    __tablename__ = "code_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # Indexed for history filtering, newest-first sorting, and issue lookups
    # (created by migration 0002_review_indexes).
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), index=True)
    submitted_code: Mapped[str] = mapped_column(Text)
    programming_language: Mapped[str] = mapped_column(String(50))
    review_status: Mapped[str] = mapped_column(String(50), default="pending")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    risk_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    risk_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    risk_breakdown: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Stage 11: set only for reviews of a GitHub pull request.
    pull_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("pull_requests.id"), nullable=True, index=True
    )

    project: Mapped["Project"] = relationship(back_populates="code_reviews")
    issues: Mapped[list["ReviewIssue"]] = relationship(back_populates="review")
    pull_request: Mapped["PullRequest | None"] = relationship()


class PullRequest(Base):
    """Stage 11: a pull request's details as they were when it was reviewed."""
    __tablename__ = "pull_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    owner: Mapped[str] = mapped_column(String(100))
    repo: Mapped[str] = mapped_column(String(100))
    number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String(500))
    author: Mapped[str] = mapped_column(String(255))
    html_url: Mapped[str] = mapped_column(String(300))
    base_sha: Mapped[str] = mapped_column(String(64))
    head_sha: Mapped[str] = mapped_column(String(64))
    source_root: Mapped[str] = mapped_column(String(240), default="")
    changed_files_count: Mapped[int] = mapped_column(Integer)
    additions: Mapped[int] = mapped_column(Integer)
    deletions: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    files: Mapped[list["PullRequestFile"]] = relationship(
        back_populates="pull_request", order_by="PullRequestFile.id"
    )


class PullRequestFile(Base):
    """Stage 11: one changed file and whether it was reviewed."""
    __tablename__ = "pull_request_files"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    pull_request_id: Mapped[int] = mapped_column(ForeignKey("pull_requests.id"), index=True)
    path: Mapped[str] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20))
    additions: Mapped[int] = mapped_column(Integer)
    deletions: Mapped[int] = mapped_column(Integer)
    patch: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    # "pending", "reviewed", "skipped" or "failed".
    review_state: Mapped[str] = mapped_column(String(20), default="pending")
    # Set when skipped: "removed", "generated", "binary", "too_large",
    # "unsupported" or "file_limit".
    skip_reason: Mapped[str | None] = mapped_column(String(30), nullable=True)

    pull_request: Mapped["PullRequest"] = relationship(back_populates="files")


class ReviewIssue(Base):
    __tablename__ = "review_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[int] = mapped_column(ForeignKey("code_reviews.id"), index=True)
    title: Mapped[str | None] = mapped_column(String(255), nullable=True)
    category: Mapped[str] = mapped_column(String(50))
    severity: Mapped[str] = mapped_column(String(20))
    file_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    explanation: Mapped[str] = mapped_column(Text)
    why_it_matters: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_fix: Mapped[str | None] = mapped_column(Text, nullable=True)
    
    #Stage 7: Confidence Score numeric evidence-based confidence score (0-100).
    confidence_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    
    #Classification of the confidence score: low, medium, or high.
    confidence_level: Mapped[str | None] = mapped_column(String(20), nullable=True)
    
    #Stores which evidence sources support the finding.
    confidence_evidence: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    
    # Tracks the developer's response to this finding. Valid values (enforced
    # with Developer Feedback, planned for Stage 12): "open", "fixed",
    # "dismissed", "false_positive".
    status: Mapped[str] = mapped_column(String(30), default="open", nullable=False)

    # Stage 11: for pull request reviews, True if the finding is not on a
    # changed line. Empty for manual reviews.
    outside_diff: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    review: Mapped["CodeReview"] = relationship(back_populates="issues")
