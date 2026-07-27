from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.social_account import SocialAccount
from app.models.user import User
from app.schemas.social_account import SocialAccountCreate, SocialAccountOut


def _to_out(account: SocialAccount) -> SocialAccountOut:
    preview = account.access_token[:6] + "..." if account.access_token else None
    return SocialAccountOut(
        id=account.id,
        organization_id=account.organization_id,
        platform=account.platform,
        account_name=account.account_name,
        created_at=account.created_at,
        access_token_preview=preview,
    )


def list_accounts(db: Session, current_user: User) -> list[SocialAccountOut]:
    accounts = (
        db.query(SocialAccount)
        .filter(SocialAccount.organization_id == current_user.organization_id)
        .order_by(SocialAccount.created_at.desc())
        .all()
    )
    return [_to_out(a) for a in accounts]


def create_account(db: Session, current_user: User, payload: SocialAccountCreate) -> SocialAccountOut:
    account = SocialAccount(
        organization_id=current_user.organization_id,
        platform=payload.platform,
        account_name=payload.account_name.strip(),
        access_token=payload.access_token,
    )
    db.add(account)
    try:
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account already exists for this platform/name in your organization",
        ) from exc
    db.refresh(account)
    return _to_out(account)


def delete_account(db: Session, current_user: User, account_id: int) -> None:
    account = (
        db.query(SocialAccount)
        .filter(
            SocialAccount.id == account_id,
            SocialAccount.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not account:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Social account not found")
    db.delete(account)
    db.commit()
