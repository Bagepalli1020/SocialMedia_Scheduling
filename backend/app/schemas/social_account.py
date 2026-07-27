from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.social_account import Platform


class SocialAccountCreate(BaseModel):
    platform: Platform
    account_name: str = Field(min_length=1, max_length=255)
    access_token: str = Field(min_length=1, max_length=512, description="Mock token is allowed")


class SocialAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    platform: Platform
    account_name: str
    created_at: datetime
    # Never expose full access_token in list responses for safety demo
    access_token_preview: str | None = None
