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

from sqlalchemy.orm import Session, joinedload

from app.config import get_settings
from app.database import SessionLocal
from app.models.analytics import Analytics
from app.models.post import Post, PostLog, PostStatus
from app.services import publisher as publisher_service
from app.utils.cache import cache_delete_pattern
from app.workers.celery_app import celery_app

settings = get_settings()


def run_publish_due_posts(db: Session, *, enqueue: bool = True) -> dict:
    """
    Find due posts. If enqueue=True, push Celery jobs; otherwise publish inline (tests).
    """
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
    return {"due_found": len(due_posts), "enqueued": processed, "checked_at": now.isoformat()}


def run_publish_post(db: Session, post_id: int) -> dict:
    """
    Publish a single post with duplicate-publish prevention.

    Lock strategy: only transition status from `scheduled` -> `publishing`.
    If another worker already claimed it, skip.
    """
    query = (
        db.query(Post)
        .options(joinedload(Post.social_account))
        .filter(Post.id == post_id)
    )
    # SELECT FOR UPDATE when supported (PostgreSQL). SQLite tests skip it.
    try:
        if db.bind and db.bind.dialect.name == "postgresql":
            query = query.with_for_update()
    except Exception:
        pass

    post = query.first()
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
