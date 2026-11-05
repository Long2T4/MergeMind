from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database.database import get_db
from app.models.models import User
from app.models.schemas import UserCreate, UserOut

router = APIRouter(prefix="/users", tags=["users"])

DUPLICATE_EMAIL = "A user with this email already exists"


@router.post("/", response_model=UserOut)
def create_user(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first() is not None:
        raise HTTPException(status_code=409, detail=DUPLICATE_EMAIL)
    db_user = User(name=user.name, email=user.email)
    db.add(db_user)
    try:
        db.commit()
    except IntegrityError as error:
        # Another request created the same email between the check and the insert.
        db.rollback()
        raise HTTPException(status_code=409, detail=DUPLICATE_EMAIL) from error
    db.refresh(db_user)
    return db_user


@router.get("/", response_model=list[UserOut])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()
