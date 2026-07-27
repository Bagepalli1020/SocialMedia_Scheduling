from datetime import datetime, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.post import Post, PostLog, PostStatus
from app.models.social_account import SocialAccount
from app.models.user import User
from app.schemas.post import PostCreate, PostOut, PostUpdate
from app.utils.cache import cache_delete_pattern


def _to_out(post: Post) -> PostOut:
    platform = None
    account_name = None
    if post.social_account:
        platform = post.social_account.platform
        account_name = post.social_account.account_name
    return PostOut(
        id=post.id,
        organization_id=post.organization_id,
        social_account_id=post.social_account_id,
        content=post.content,
        scheduled_time=post.scheduled_time,
        status=post.status,
        retry_count=post.retry_count,
        created_at=post.created_at,
        platform=platform,
        account_name=account_name,
    )


def _ensure_future(scheduled_time: datetime) -> datetime:
    now = datetime.now(timezone.utc)
    compare = scheduled_time if scheduled_time.tzinfo else scheduled_time.replace(tzinfo=timezone.utc)
    if compare <= now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="scheduled_time must be in the future",
        )
    return compare


def list_posts(db: Session, current_user: User, status_filter: PostStatus | None = None) -> list[PostOut]:
    query = (
        db.query(Post)
        .options(joinedload(Post.social_account))
        .filter(Post.organization_id == current_user.organization_id)
    )
    if status_filter:
        query = query.filter(Post.status == status_filter)
    posts = query.order_by(Post.scheduled_time.desc()).all()
    return [_to_out(p) for p in posts]


def get_post(db: Session, current_user: User, post_id: int) -> PostOut:
    post = (
        db.query(Post)
        .options(joinedload(Post.social_account))
        .filter(Post.id == post_id, Post.organization_id == current_user.organization_id)
        .first()
    )
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return _to_out(post)


def create_post(db: Session, current_user: User, payload: PostCreate) -> PostOut:
    scheduled_time = _ensure_future(payload.scheduled_time)

    account = (
        db.query(SocialAccount)
        .filter(
            SocialAccount.id == payload.social_account_id,
            SocialAccount.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Social account not found in your organization",
        )

    post = Post(
        organization_id=current_user.organization_id,
        social_account_id=account.id,
        content=payload.content.strip(),
        scheduled_time=scheduled_time,
        status=PostStatus.scheduled,
    )
    db.add(post)
    db.commit()
    db.refresh(post)
    post = (
        db.query(Post)
        .options(joinedload(Post.social_account))
        .filter(Post.id == post.id)
        .first()
    )
    cache_delete_pattern(f"analytics:org:{current_user.organization_id}:*")
    return _to_out(post)


def update_post(db: Session, current_user: User, post_id: int, payload: PostUpdate) -> PostOut:
    post = (
        db.query(Post)
        .options(joinedload(Post.social_account))
        .filter(Post.id == post_id, Post.organization_id == current_user.organization_id)
        .first()
    )
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.status != PostStatus.scheduled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only scheduled posts can be updated",
        )

    if payload.content is not None:
        post.content = payload.content.strip()
    if payload.scheduled_time is not None:
        post.scheduled_time = _ensure_future(payload.scheduled_time)

    db.commit()
    db.refresh(post)
    cache_delete_pattern(f"analytics:org:{current_user.organization_id}:*")
    return _to_out(post)


def delete_post(db: Session, current_user: User, post_id: int) -> None:
    post = (
        db.query(Post)
        .filter(Post.id == post_id, Post.organization_id == current_user.organization_id)
        .first()
    )
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    if post.status == PostStatus.publishing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete a post that is currently publishing",
        )
    db.delete(post)
    db.commit()
    cache_delete_pattern(f"analytics:org:{current_user.organization_id}:*")


def get_post_logs(db: Session, current_user: User, post_id: int) -> list[PostLog]:
    post = (
        db.query(Post)
        .filter(Post.id == post_id, Post.organization_id == current_user.organization_id)
        .first()
    )
    if not post:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Post not found")
    return (
        db.query(PostLog)
        .filter(PostLog.post_id == post_id)
        .order_by(PostLog.executed_at.desc())
        .all()
    )
