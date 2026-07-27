from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth.security import create_access_token, hash_password, verify_password
from app.models.organization import Organization
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, Token


def register_user(db: Session, payload: RegisterRequest) -> tuple[User, Token]:
    existing = db.query(User).filter(User.email == payload.email.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    existing_org = (
        db.query(Organization).filter(Organization.name == payload.organization_name.strip()).first()
    )
    if existing_org:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Organization name already taken",
        )

    organization = Organization(name=payload.organization_name.strip())
    db.add(organization)
    db.flush()

    # First user of a new organization is always admin for multi-tenant bootstrap
    user = User(
        email=payload.email.lower(),
        hashed_password=hash_password(payload.password),
        role=UserRole.admin,
        organization_id=organization.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = Token(
        access_token=create_access_token(
            user_id=user.id,
            organization_id=user.organization_id,
            role=user.role,
            email=user.email,
        )
    )
    return user, token


def login_user(db: Session, payload: LoginRequest) -> Token:
    user = db.query(User).filter(User.email == payload.email.lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    return Token(
        access_token=create_access_token(
            user_id=user.id,
            organization_id=user.organization_id,
            role=user.role,
            email=user.email,
        )
    )


def add_member(
    db: Session,
    *,
    organization_id: int,
    email: str,
    password: str,
    role: UserRole = UserRole.member,
) -> User:
    existing = db.query(User).filter(User.email == email.lower()).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    user = User(
        email=email.lower(),
        hashed_password=hash_password(password),
        role=role,
        organization_id=organization_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
