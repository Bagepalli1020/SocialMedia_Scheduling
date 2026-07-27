from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.analytics import Analytics
from app.models.post import Post, PostStatus
from app.models.user import User
from app.schemas.analytics import DashboardStats, EngagementTrend
from app.utils.cache import cache_get, cache_set


def get_dashboard_stats(db: Session, current_user: User) -> DashboardStats:
    org_id = current_user.organization_id
    cache_key = f"analytics:org:{org_id}:dashboard"
    cached = cache_get(cache_key)
    if cached:
        return DashboardStats(**cached)

    base = db.query(Post).filter(Post.organization_id == org_id)
    total_posts = base.count()
    scheduled_posts = base.filter(Post.status == PostStatus.scheduled).count()
    published_posts = base.filter(Post.status == PostStatus.published).count()
    failed_posts = base.filter(Post.status == PostStatus.failed).count()

    totals = (
        db.query(
            func.coalesce(func.sum(Analytics.views), 0),
            func.coalesce(func.sum(Analytics.likes), 0),
            func.coalesce(func.sum(Analytics.shares), 0),
        )
        .join(Post, Post.id == Analytics.post_id)
        .filter(Post.organization_id == org_id)
        .one()
    )

    # Performance trends by day (published posts + their analytics)
    rows = (
        db.query(
            func.date(Post.scheduled_time).label("day"),
            func.count(Post.id),
            func.coalesce(func.sum(Analytics.views), 0),
            func.coalesce(func.sum(Analytics.likes), 0),
            func.coalesce(func.sum(Analytics.shares), 0),
        )
        .outerjoin(Analytics, Analytics.post_id == Post.id)
        .filter(Post.organization_id == org_id)
        .group_by(func.date(Post.scheduled_time))
        .order_by(func.date(Post.scheduled_time).asc())
        .all()
    )

    trends: list[EngagementTrend] = []
    for day, posts_count, views, likes, shares in rows:
        day_str = day.isoformat() if hasattr(day, "isoformat") else str(day)
        trends.append(
            EngagementTrend(
                date=day_str,
                posts=int(posts_count or 0),
                views=int(views or 0),
                likes=int(likes or 0),
                shares=int(shares or 0),
            )
        )

    stats = DashboardStats(
        total_posts=total_posts,
        scheduled_posts=scheduled_posts,
        published_posts=published_posts,
        failed_posts=failed_posts,
        total_views=int(totals[0] or 0),
        total_likes=int(totals[1] or 0),
        total_shares=int(totals[2] or 0),
        trends=trends,
    )
    cache_set(cache_key, stats.model_dump(), ttl_seconds=60)
    return stats


def get_post_analytics(db: Session, current_user: User, post_id: int) -> Analytics | None:
    post = (
        db.query(Post)
        .filter(Post.id == post_id, Post.organization_id == current_user.organization_id)
        .first()
    )
    if not post:
        return None
    return db.query(Analytics).filter(Analytics.post_id == post_id).first()
