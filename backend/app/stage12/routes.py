"""Stage 12 endpoints; every route depends on the signed-in user and checks ownership."""
from __future__ import annotations
from collections import Counter, defaultdict
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import Project, CodeReview, ReviewIssue
from app.stage12.security import CurrentUser, get_current_user

router = APIRouter(prefix='/account', tags=['Stage 12 - account and learning'])


class NewProject(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=4000)

class FindingStatus(BaseModel):
    status: Literal['open', 'fixed', 'dismissed', 'false_positive']


def serialize_project(project):
    return {'id': project.id, 'name': project.name, 'description': project.description}


@router.get('/me')
def get_me(user: CurrentUser = Depends(get_current_user)):
    return {'id': user.id, 'name': user.name, 'email': user.email}


@router.get('/projects')
def list_projects(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    uid = user.id
    projects = db.query(Project).filter(Project.user_id == uid).order_by(Project.id.desc()).all()
    return [serialize_project(p) for p in projects]


@router.post('/projects', status_code=201)
def create_project(body: NewProject, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    uid = user.id
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail='Project name cannot be blank')
    project = Project(user_id=uid, name=name, description=body.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return serialize_project(project)


@router.get('/projects/{project_id}')
def get_project(project_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    uid = user.id
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == uid).first()
    if not project:
        raise HTTPException(status_code=404, detail='Project not found')
    return serialize_project(project)


@router.get('/reviews/{review_id}/findings')
def review_findings(review_id: int, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    uid = user.id
    review = (
        db.query(CodeReview)
        .join(Project, Project.id == CodeReview.project_id)
        .filter(CodeReview.id == review_id, Project.user_id == uid)
        .first()
    )
    if not review:
        raise HTTPException(status_code=404, detail='Review not found')
    issues = db.query(ReviewIssue).filter(ReviewIssue.review_id == review_id).order_by(ReviewIssue.id).all()
    return [
        {'id': issue.id, 'title': getattr(issue, 'title', '') or 'Finding',
         'category': issue.category, 'severity': issue.severity,
         'status': issue.status or 'open'}
        for issue in issues
    ]


@router.patch('/findings/{issue_id}')
def update_status(issue_id: int, body: FindingStatus, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    uid = user.id
    issue = (
        db.query(ReviewIssue)
        .join(CodeReview, CodeReview.id == ReviewIssue.review_id)
        .join(Project, Project.id == CodeReview.project_id)
        .filter(ReviewIssue.id == issue_id, Project.user_id == uid)
        .first()
    )
    if not issue:
        raise HTTPException(status_code=404, detail='Finding not found')
    issue.status = body.status  # Only outcome is edited; Stage 13 analysis untouched.
    db.commit()
    db.refresh(issue)
    return {'id': issue.id, 'status': issue.status}


CATEGORIES = ('Security','Testing','Error Handling','Input Validation','Database','Performance','Code Quality','Logic')

def normalize_category(value: str | None) -> str:
    key = (value or '').strip().lower().replace('-', ' ').replace('_', ' ')
    return next((cat for cat in CATEGORIES if cat.lower() == key), 'Other')


def learning_metrics(reviews, findings):
    """Pure function; safe to test without a database. Dates are *review creation* dates."""
    statuses = Counter({'open': 0, 'fixed': 0, 'dismissed': 0, 'false_positive': 0})
    category_count = Counter()
    category_review_ids = defaultdict(set)
    by_month = defaultdict(lambda: Counter())
    review_by_id = {r.id: r for r in reviews}
    for issue in findings:
        status = issue.status if issue.status in statuses else 'open'
        statuses[status] += 1
        category = normalize_category(issue.category)
        category_count[category] += 1
        category_review_ids[category].add(issue.review_id)
        review = review_by_id.get(issue.review_id)
        if review and review.created_at:
            date = review.created_at
            month = date.strftime('%Y-%m')
            by_month[month][category] += 1
    return {
        'total_reviews': len(reviews),
        'total_issues': len(findings),
        'fixed_issues': statuses['fixed'],
        'false_positives': statuses['false_positive'],
        'statuses': dict(statuses),
        'categories': dict(sorted(category_count.items(), key=lambda c: (-c[1], c[0]))),
        'repeated_categories': [
            {'category': category, 'review_count': len(ids)}
            for category, ids in sorted(category_review_ids.items(), key=lambda kv: (-len(kv[1]), kv[0]))
            if len(ids) > 1
        ],
        'monthly_categories': [
            {'month': month, 'categories': dict(count)}
            for month, count in sorted(by_month.items())
        ],
        'trend_note': 'Monthly categories use review creation dates, not the dates feedback was updated.',
    }


@router.get('/learning')
def get_learning(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    uid = user.id
    reviews = (
        db.query(CodeReview)
        .join(Project, CodeReview.project_id == Project.id)
        .filter(Project.user_id == uid)
        .order_by(CodeReview.created_at.desc())
        .all()
    )
    review_ids = [r.id for r in reviews]
    findings = (
        db.query(ReviewIssue).filter(ReviewIssue.review_id.in_(review_ids)).all()
        if review_ids else []
    )
    data = learning_metrics(reviews, findings)
    # One CodeReview is counted once even if it has many findings/files.
    data['pull_request_reviews'] = sum(1 for r in reviews if getattr(r, 'pull_request_id', None) is not None)
    return data
