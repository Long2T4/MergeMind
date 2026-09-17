from datetime import datetime

from pydantic import BaseModel


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


class CodeReviewCreate(BaseModel):
    project_id: int
    submitted_code: str
    programming_language: str


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
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class CodeReviewOut(BaseModel):
    id: int
    project_id: int
    submitted_code: str
    programming_language: str
    review_status: str
    created_at: datetime
    issues: list[ReviewIssueOut] = []

    class Config:
        from_attributes = True
