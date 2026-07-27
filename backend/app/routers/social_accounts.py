from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user, require_admin
from app.database import get_db
from app.models.user import User
from app.schemas.social_account import SocialAccountCreate, SocialAccountOut
from app.services import social_account_service

router = APIRouter(prefix="/social-accounts", tags=["Social Accounts"])


@router.get("", response_model=list[SocialAccountOut])
def list_social_accounts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return social_account_service.list_accounts(db, current_user)


@router.post("", response_model=SocialAccountOut, status_code=status.HTTP_201_CREATED)
def create_social_account(
    payload: SocialAccountCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Admin-only: connect a social media account (mock token allowed)."""
    return social_account_service.create_account(db, current_user, payload)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_social_account(
    account_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    social_account_service.delete_account(db, current_user, account_id)
    return None
