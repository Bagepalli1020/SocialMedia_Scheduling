"""Mock external social media API integration."""

from __future__ import annotations

import random
import time
import uuid
from dataclasses import dataclass

from app.models.social_account import Platform, SocialAccount


@dataclass
class PublishResult:
    success: bool
    platform_post_id: str | None
    response: str
    views: int = 0
    likes: int = 0
    shares: int = 0


def mock_publish_to_platform(account: SocialAccount, content: str) -> PublishResult:
    """
    Simulate calling Twitter / Instagram / LinkedIn APIs.
    Randomly fails ~10% of the time to exercise retry / failed status logic.
    """
    # Simulate short network latency
    time.sleep(0.01)

    # Simulate invalid token failure
    if not account.access_token or account.access_token.lower() in {"invalid", "expired"}:
        return PublishResult(
            success=False,
            platform_post_id=None,
            response=f"[{account.platform.value}] Authentication failed: invalid or expired access token",
        )

    # Random transient failure (~10%)
    if random.random() < 0.10:
        return PublishResult(
            success=False,
            platform_post_id=None,
            response=f"[{account.platform.value}] Temporary API error: rate limit or network timeout",
        )

    platform_post_id = f"{account.platform.value}_{uuid.uuid4().hex[:12]}"
    # Seed mock engagement numbers
    base = max(10, len(content) // 2)
    views = random.randint(base, base * 20)
    likes = random.randint(1, max(2, views // 5))
    shares = random.randint(0, max(1, likes // 3))

    platform_label = {
        Platform.twitter: "Twitter/X",
        Platform.instagram: "Instagram",
        Platform.linkedin: "LinkedIn",
    }.get(account.platform, account.platform.value)

    response = (
        f"Successfully published to {platform_label} account '{account.account_name}'. "
        f"platform_post_id={platform_post_id}"
    )
    return PublishResult(
        success=True,
        platform_post_id=platform_post_id,
        response=response,
        views=views,
        likes=likes,
        shares=shares,
    )
