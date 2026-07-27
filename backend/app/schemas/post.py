from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.post import PostStatus
from app.models.social_account import Platform


class PostCreate(BaseModel):
    content: str = Field(min_length=1, max_length=5000)
    scheduled_time: datetime
    social_account_id: int

    @field_validator("scheduled_time")
    @classmethod
    def scheduled_time_must_be_future(cls, value: datetime) -> datetime:
        # Normalize naive datetimes to UTC-aware comparison by treating as UTC
        from datetime import timezone

        now = datetime.now(timezone.utc)
        compare = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if compare <= now:
            raise ValueError("scheduled_time must be in the future")
        return value


class PostUpdate(BaseModel):
    content: str | None = Field(default=None, min_length=1, max_length=5000)
    scheduled_time: datetime | None = None

    @field_validator("scheduled_time")
    @classmethod
    def scheduled_time_must_be_future(cls, value: datetime | None) -> datetime | None:
        if value is None:
            return value
        from datetime import timezone

        now = datetime.now(timezone.utc)
        compare = value if value.tzinfo else value.replace(tzinfo=timezone.utc)
        if compare <= now:
            raise ValueError("scheduled_time must be in the future")
        return value


class PostLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    post_id: int
    status: str
    response: str | None
    executed_at: datetime


class PostOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    social_account_id: int
    content: str
    scheduled_time: datetime
    status: PostStatus
    retry_count: int
    created_at: datetime
    platform: Platform | None = None
    account_name: str | None = None
