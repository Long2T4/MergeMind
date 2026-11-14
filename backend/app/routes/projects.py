from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import Project, User
from app.models.schemas import ProjectCreate, ProjectOut
from app.stage12.security import CurrentUser, get_current_user

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("/", response_model=ProjectOut)
def create_project(
    project: ProjectCreate, db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user),
):
    # Stage 12: projects can only be created for the signed-in user. Another
    # user's id gets the same 404 as a missing one, so it reveals nothing.
    if project.user_id != user.id or db.get(User, project.user_id) is None:
        raise HTTPException(status_code=404, detail="User not found")
    db_project = Project(
        user_id=project.user_id,
        name=project.name,
        description=project.description,
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    return db_project


@router.get("/", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db), user: CurrentUser = Depends(get_current_user)):
    return db.query(Project).filter(Project.user_id == user.id).all()
