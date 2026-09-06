from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.auth import LoginIn, MeOut, RegisterIn, TokenOut
from app.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    email = payload.email.lower().strip()
    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=400, detail="Email is already registered")

    user = User(
        email=email,
        password_hash=hash_password(payload.password),
        role="student",  # role escalation is never client-controlled
        display_name=payload.display_name or email.split("@")[0],
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return TokenOut(
        access_token=create_access_token(str(user.id), user.role),
        role=user.role,
        user_id=user.id,
        email=user.email,
    )


@router.post("/login", response_model=TokenOut)
def login(payload: LoginIn, db: Session = Depends(get_db)) -> TokenOut:
    email = payload.email.lower().strip()
    user = db.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    return TokenOut(
        access_token=create_access_token(str(user.id), user.role),
        role=user.role,
        user_id=user.id,
        email=user.email,
    )


@router.get("/me", response_model=MeOut)
def me(user: User = Depends(get_current_user)) -> MeOut:
    return MeOut(
        id=user.id,
        email=user.email,
        role=user.role,
        display_name=user.display_name,
        is_active=user.is_active,
    )
