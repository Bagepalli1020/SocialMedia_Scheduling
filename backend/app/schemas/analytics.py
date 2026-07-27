from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AnalyticsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    views: int
    likes: int
    shares: int
    updated_at: datetime


class EngagementTrend(BaseModel):
    date: str
    views: int
    likes: int
    shares: int
    posts: int


class DashboardStats(BaseModel):
    total_posts: int
    scheduled_posts: int
    published_posts: int
    failed_posts: int
    total_views: int
    total_likes: int
    total_shares: int
    trends: list[EngagementTrend]
