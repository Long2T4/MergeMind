"""Stage 12: finding feedback (who and when), project renaming and Learning
outcomes by category, through the real API as two signed-in users."""
from datetime import datetime, timedelta

from app.models.models import Project, ReviewIssue
from app.stage12.routes import learning_metrics
from test_stage12_authorization import A, B, env  # noqa: F401 (pytest fixture)


# --- Who changed a finding's status, and when -------------------------------------

def test_a_status_change_records_who_and_when(env):
    issue_id = env.ids["A"].issue
    before = datetime.utcnow() - timedelta(seconds=5)
    response = env.client.patch(f"/account/findings/{issue_id}", headers=A, json={"status": "fixed"})
    assert response.status_code == 200
    body = response.json()
    assert (body["id"], body["status"], body["status_updated_by"]) == (issue_id, "fixed", env.ids["A"].user)
    assert datetime.fromisoformat(body["status_updated_at"]) >= before

    with env.factory() as db:
        saved = db.get(ReviewIssue, issue_id)
        assert (saved.status, saved.status_updated_by) == ("fixed", env.ids["A"].user)
        assert saved.status_updated_at is not None

    detail = env.client.get(f"/review-history/{env.ids['A'].review}", headers=A).json()
    assert (detail["issues"][0]["status"], detail["issues"][0]["status_updated_by"]) == ("fixed", env.ids["A"].user)
    findings = env.client.get(f"/account/reviews/{env.ids['A'].review}/findings", headers=A).json()
    assert findings[0]["status"] == "fixed" and findings[0]["status_updated_at"]


def test_every_allowed_status_can_be_set_and_others_are_refused(env):
    issue_id = env.ids["A"].issue
    for status in ("dismissed", "false_positive", "open", "fixed"):
        assert env.client.patch(f"/account/findings/{issue_id}", headers=A, json={"status": status}).status_code == 200
    for bad in ("resolved", "FIXED", "", None):
        assert env.client.patch(f"/account/findings/{issue_id}", headers=A, json={"status": bad}).status_code == 422
    with env.factory() as db:
        assert db.get(ReviewIssue, issue_id).status == "fixed"


def test_untouched_findings_have_no_who_or_when(env):
    detail = env.client.get(f"/review-history/{env.ids['B'].review}", headers=B).json()
    assert (detail["issues"][0]["status"], detail["issues"][0]["status_updated_at"]) == ("open", None)


# --- Renaming projects ----------------------------------------------------------

def test_owners_can_rename_their_projects(env):
    project_id = env.ids["A"].project
    response = env.client.patch(f"/account/projects/{project_id}", headers=A,
                                json={"name": "  Renamed project  ", "description": "New description"})
    assert response.status_code == 200
    assert response.json() == {"id": project_id, "name": "Renamed project", "description": "New description"}
    assert [p["name"] for p in env.client.get("/projects/", headers=A).json()] == ["Renamed project"]


def test_renaming_keeps_the_description_unless_one_is_given(env):
    project_id = env.ids["A"].project
    env.client.patch(f"/account/projects/{project_id}", headers=A, json={"name": "One", "description": "Kept"})
    response = env.client.patch(f"/account/projects/{project_id}", headers=A, json={"name": "Two"})
    assert response.json()["description"] == "Kept"


def test_blank_names_and_other_users_projects_are_refused(env):
    for name in ("", "   "):
        assert env.client.patch(f"/account/projects/{env.ids['A'].project}", headers=A, json={"name": name}).status_code == 422
    assert env.client.patch(f"/account/projects/{env.ids['B'].project}", headers=A, json={"name": "Mine now"}).status_code == 404
    with env.factory() as db:
        assert db.get(Project, env.ids["B"].project).name == "B project"
        assert db.get(Project, env.ids["A"].project).name == "A project"


# --- Learning outcomes by category ---------------------------------------------

def test_learning_shows_outcomes_by_category_traceable_to_findings(env):
    with env.factory() as db:
        review_id = env.ids["A"].review
        db.add_all([
            ReviewIssue(review_id=review_id, category="logic", severity="low", explanation="e", status="fixed"),
            ReviewIssue(review_id=review_id, category="security", severity="high", explanation="e", status="false_positive"),
            ReviewIssue(review_id=review_id, category="security", severity="high", explanation="e", status="dismissed"),
        ])
        db.commit()

    learning = env.client.get("/account/learning", headers=A).json()
    outcomes = learning["category_outcomes"]
    assert outcomes["Logic"] == {"open": 1, "fixed": 1, "dismissed": 0, "false_positive": 0}
    assert outcomes["Security"] == {"open": 0, "fixed": 0, "dismissed": 1, "false_positive": 1}
    # Every outcome is a saved finding: per-category totals match the category counts.
    for category, counts in outcomes.items():
        assert sum(counts.values()) == learning["categories"][category]
    assert sum(learning["statuses"].values()) == learning["total_issues"] == 4
    # B's findings never appear in A's numbers.
    assert env.client.get("/account/learning", headers=B).json()["total_issues"] == 1


def test_learning_metrics_treats_unknown_statuses_as_open():
    review = type("R", (), {"id": 1, "created_at": datetime(2026, 11, 1)})()
    finding = type("F", (), {"review_id": 1, "category": "logic", "status": None})()
    metrics = learning_metrics([review], [finding])
    assert metrics["category_outcomes"] == {"Logic": {"open": 1, "fixed": 0, "dismissed": 0, "false_positive": 0}}
