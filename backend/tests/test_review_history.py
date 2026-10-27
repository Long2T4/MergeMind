"""FastAPI endpoint tests: run from backend/: pytest tests/test_review_history.py -q

Uses in-memory SQLite, not Supabase, and never calls the AI service.
"""
import os

os.environ.setdefault("DATABASE_URL", "sqlite://")

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.database import Base, get_db
from app.models.models import User, Project, CodeReview, ReviewIssue
from app.routes.review_history import router


def make_client():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    db = session_factory()
    try:
        user = User(name="Stage Six Student", email="stage6@example.com")
        db.add(user)
        db.flush()
        project = Project(user_id=user.id, name="History Project")
        db.add(project)
        db.flush()
        review = CodeReview(
            project_id=project.id,
            submitted_code="print('hello')",
            programming_language="python",
            review_status="completed",
        )
        db.add(review)
        db.flush()
        db.add(ReviewIssue(
            review_id=review.id,
            category="Security",
            severity="high",
            explanation="Example security finding",
            status="open",
        ))
        db.commit()
    finally:
        db.close()

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        with session_factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), engine


def add_reviews(engine, *reviews):
    """Insert extra reviews into project 1: each item is (code, language, status)."""
    with sessionmaker(bind=engine)() as db:
        for code, language, status in reviews:
            db.add(CodeReview(
                project_id=1,
                submitted_code=code,
                programming_language=language,
                review_status=status,
            ))
        db.commit()


def test_history_list_and_filters():
    client, engine = make_client()
    try:
        result = client.get("/review-history/")
        assert result.status_code == 200
        body = result.json()
        assert body["total"] == 1
        assert body["items"][0]["programming_language"] == "python"
        assert body["items"][0]["issue_count"] == 1
        assert client.get("/review-history/?language=java").json()["total"] == 0
        assert client.get("/review-history/?q=hello").json()["total"] == 1
        assert client.get("/review-history/?offset=1").json()["items"] == []
    finally:
        client.close()
        engine.dispose()


def test_history_statistics():
    client, engine = make_client()
    try:
        result = client.get("/review-history/stats")
        assert result.status_code == 200
        assert result.json() == {
            "total_reviews": 1,
            "completed_reviews": 1,
            "total_issues": 1,
            "high_severity_issues": 1,
        }
    finally:
        client.close()
        engine.dispose()


def test_invalid_page_inputs_rejected():
    client, engine = make_client()
    try:
        assert client.get("/review-history/?limit=999").status_code == 422
        assert client.get("/review-history/?offset=-2").status_code == 422
    finally:
        client.close()
        engine.dispose()


def test_list_items_are_lightweight_summaries():
    client, engine = make_client()
    try:
        add_reviews(engine, ("x" * 500, "python", "completed"))
        items = client.get("/review-history/").json()["items"]
        newest, seeded = items[0], items[1]
        # Full code and issue bodies are only returned by the detail endpoint.
        assert "submitted_code" not in newest
        assert "issues" not in newest
        assert len(newest["code_preview"]) == 160
        assert newest["issue_count"] == 0
        assert seeded["code_preview"] == "print('hello')"
        assert seeded["issue_count"] == 1
        assert seeded["high_severity_count"] == 1
    finally:
        client.close()
        engine.dispose()


def test_language_filter_uses_stored_values():
    client, engine = make_client()
    try:
        add_reviews(
            engine,
            ("int main() {}", "cpp", "completed"),
            ("int main(void) {}", "c", "completed"),
            ("???", "other", "failed"),
        )
        # The submit form stores "cpp", never "c++".
        assert client.get("/review-history/?language=cpp").json()["total"] == 1
        assert client.get("/review-history/?language=c%2B%2B").json()["total"] == 0
        # "c" must match exactly, not also "cpp".
        c_items = client.get("/review-history/?language=c").json()["items"]
        assert [item["programming_language"] for item in c_items] == ["c"]
        assert client.get("/review-history/?language=other").json()["total"] == 1
        assert client.get("/review-history/?language=PYTHON").json()["total"] == 1
    finally:
        client.close()
        engine.dispose()


def test_search_treats_like_wildcards_literally():
    client, engine = make_client()
    try:
        add_reviews(
            engine,
            ("discount = price * 50%", "python", "completed"),
            ("user_name = 'a'", "python", "completed"),
            (r"path = 'C:\temp'", "python", "completed"),
        )
        # Before the fix, "%" and "_" matched every review.
        assert client.get("/review-history/?q=%25").json()["total"] == 1
        assert client.get("/review-history/?q=_").json()["total"] == 1
        assert client.get("/review-history/?q=user_name").json()["total"] == 1
        assert client.get("/review-history/?q=user%25name").json()["total"] == 0
        assert client.get("/review-history/?q=%5C").json()["total"] == 1
    finally:
        client.close()
        engine.dispose()


def test_review_detail_returns_full_review():
    client, engine = make_client()
    try:
        result = client.get("/review-history/1")
        assert result.status_code == 200
        body = result.json()
        assert body["submitted_code"] == "print('hello')"
        assert len(body["issues"]) == 1
        assert body["issues"][0]["severity"] == "high"
    finally:
        client.close()
        engine.dispose()


def test_review_detail_missing_review_returns_404():
    client, engine = make_client()
    try:
        assert client.get("/review-history/999").status_code == 404
        assert client.get("/review-history/0").status_code == 422
    finally:
        client.close()
        engine.dispose()


def test_statistics_follow_active_filters():
    client, engine = make_client()
    try:
        add_reviews(engine, ("int main() {}", "cpp", "failed"))
        everything = client.get("/review-history/stats").json()
        assert everything["total_reviews"] == 2
        assert everything["completed_reviews"] == 1
        assert client.get("/review-history/stats?language=cpp").json() == {
            "total_reviews": 1,
            "completed_reviews": 0,
            "total_issues": 0,
            "high_severity_issues": 0,
        }
        assert client.get("/review-history/stats?q=hello").json()["total_issues"] == 1
        assert client.get("/review-history/stats?status=failed").json()["total_reviews"] == 1
    finally:
        client.close()
        engine.dispose()
