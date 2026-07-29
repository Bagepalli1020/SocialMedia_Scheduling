"""
Scheduling architecture (background jobs):

1. Celery Beat runs `publish_due_posts` every SCHEDULER_INTERVAL_SECONDS.
2. That task finds posts where status=scheduled and scheduled_time <= now.
3. For each due post it enqueues `publish_post(post_id)`.
4. `publish_post` uses a status lock (scheduled -> publishing) to prevent duplicates,
   calls the mock platform API, writes PostLog, updates status, and creates Analytics.
5. On failure, retry_count increments; post is re-scheduled or marked failed.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionLocal
from app.models.analytics import Analytics
from app.models.post import Post, PostLog, PostStatus
from app.services import publisher as publisher_service
from app.utils.cache import cache_delete_pattern
from app.workers.celery_app import celery_app

settings = get_settings()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def reclaim_stuck_publishing_posts(db: Session, *, older_than_seconds: int = 120) -> int:
    """
    Recover posts stuck in `publishing` (e.g. worker crashed mid-publish).
    Sets them back to `scheduled` so they can be claimed again.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=older_than_seconds)
    stuck_ids: set[int] = set()
    publishing_posts = db.query(Post).filter(Post.status == PostStatus.publishing).all()
    for post in publishing_posts:
        latest = (
            db.query(PostLog)
            .filter(PostLog.post_id == post.id, PostLog.status == "publishing")
            .order_by(PostLog.executed_at.desc())
            .first()
        )
        executed_at = _as_utc(latest.executed_at if latest else post.created_at)
        if executed_at <= cutoff:
            stuck_ids.add(post.id)

    reclaimed = 0
    now = datetime.now(timezone.utc)
    for post_id in stuck_ids:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post or post.status != PostStatus.publishing:
            continue
        post.status = PostStatus.scheduled
        if _as_utc(post.scheduled_time) > now:
            post.scheduled_time = now - timedelta(seconds=1)
        db.add(
            PostLog(
                post_id=post.id,
                status="reclaimed",
                response="Reclaimed stuck publishing post for retry",
            )
        )
        reclaimed += 1
    if reclaimed:
        db.commit()
    return reclaimed


def run_publish_due_posts(db: Session, *, enqueue: bool = True) -> dict:
    """
    Find due posts. If enqueue=True, push Celery jobs; otherwise publish inline (tests).
    """
    reclaimed = reclaim_stuck_publishing_posts(db)
    now = datetime.now(timezone.utc)
    due_posts = (
        db.query(Post)
        .filter(Post.status == PostStatus.scheduled, Post.scheduled_time <= now)
        .order_by(Post.scheduled_time.asc())
        .limit(100)
        .all()
    )
    processed = 0
    for post in due_posts:
        if enqueue:
            publish_post.delay(post.id)
        else:
            run_publish_post(db, post.id)
        processed += 1
    return {
        "due_found": len(due_posts),
        "enqueued": processed,
        "reclaimed": reclaimed,
        "checked_at": now.isoformat(),
    }


def run_publish_post(db: Session, post_id: int) -> dict:
    """
    Publish a single post with duplicate-publish prevention.

    Lock strategy: only transition status from `scheduled` -> `publishing`.
    If another worker already claimed it, skip.
    """
    # Lock the post row alone first (FOR UPDATE + LEFT JOIN is invalid on PostgreSQL).
    query = db.query(Post).filter(Post.id == post_id)
    try:
        if db.bind and db.bind.dialect.name == "postgresql":
            query = query.with_for_update()
    except Exception:
        pass

    post = query.first()
    if post:
        # Load related account after the lock, without joining in the FOR UPDATE query.
        _ = post.social_account
    if not post:
        return {"post_id": post_id, "result": "not_found"}

    if post.status == PostStatus.published:
        return {"post_id": post_id, "result": "already_published"}

    if post.status == PostStatus.publishing:
        return {"post_id": post_id, "result": "already_publishing"}

    if post.status == PostStatus.failed:
        return {"post_id": post_id, "result": "already_failed"}

    if post.status != PostStatus.scheduled:
        return {"post_id": post_id, "result": f"skipped_status_{post.status}"}

    # Claim the post (prevents duplicate publishing)
    post.status = PostStatus.publishing
    db.add(
        PostLog(
            post_id=post.id,
            status="publishing",
            response="Claimed by worker for publishing",
        )
    )
    db.commit()

    account = post.social_account
    if not account:
        post.status = PostStatus.failed
        db.add(
            PostLog(
                post_id=post.id,
                status="failed",
                response="Social account missing",
            )
        )
        db.commit()
        return {"post_id": post_id, "result": "failed_missing_account"}

    result = publisher_service.mock_publish_to_platform(account, post.content)

    if result.success:
        post.status = PostStatus.published
        db.add(
            PostLog(
                post_id=post.id,
                status="published",
                response=result.response,
            )
        )
        analytics = db.query(Analytics).filter(Analytics.post_id == post.id).first()
        if not analytics:
            analytics = Analytics(post_id=post.id)
            db.add(analytics)
        analytics.views = result.views
        analytics.likes = result.likes
        analytics.shares = result.shares
        db.commit()
        cache_delete_pattern(f"analytics:org:{post.organization_id}:*")
        return {
            "post_id": post_id,
            "result": "published",
            "platform_post_id": result.platform_post_id,
        }

    # Failure path with optional retry
    post.retry_count += 1
    db.add(
        PostLog(
            post_id=post.id,
            status="failed_attempt",
            response=result.response,
        )
    )

    if post.retry_count < settings.MAX_PUBLISH_RETRIES:
        post.status = PostStatus.scheduled
        post.scheduled_time = datetime.now(timezone.utc) + timedelta(seconds=30 * post.retry_count)
        db.add(
            PostLog(
                post_id=post.id,
                status="retry_scheduled",
                response=f"Retry {post.retry_count}/{settings.MAX_PUBLISH_RETRIES} scheduled",
            )
        )
        db.commit()
        return {"post_id": post_id, "result": "retry_scheduled", "retry_count": post.retry_count}

    post.status = PostStatus.failed
    db.add(
        PostLog(
            post_id=post.id,
            status="failed",
            response=f"Max retries reached. Last error: {result.response}",
        )
    )
    db.commit()
    cache_delete_pattern(f"analytics:org:{post.organization_id}:*")
    return {"post_id": post_id, "result": "failed", "retry_count": post.retry_count}


@celery_app.task(name="app.workers.tasks.publish_due_posts")
def publish_due_posts() -> dict:
    db = SessionLocal()
    try:
        return run_publish_due_posts(db, enqueue=True)
    finally:
        db.close()


@celery_app.task(name="app.workers.tasks.publish_post", bind=True, max_retries=0)
def publish_post(self, post_id: int) -> dict:
    db = SessionLocal()
    try:
        return run_publish_post(db, post_id)
    finally:
        db.close()
