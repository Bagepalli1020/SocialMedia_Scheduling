from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, Token
from app.schemas.user import UserOut
from app.services import auth_service
from pydantic import BaseModel, EmailStr, Field

router = APIRouter(prefix="/auth", tags=["Authentication"])


class AddMemberRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    role: UserRole = UserRole.member


@router.post("/register", response_model=Token)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """Register a new organization + first admin user."""
    _, token = auth_service.register_user(db, payload)
    return token


@router.post("/login", response_model=Token)
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    return auth_service.login_user(db, payload)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/members", response_model=UserOut)
def add_member(
    payload: AddMemberRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin-only: add a member to the same organization (tenant isolation)."""
    return auth_service.add_member(
        db,
        organization_id=current_user.organization_id,
        email=payload.email,
        password=payload.password,
        role=payload.role,
    )
