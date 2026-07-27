from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.database import get_db
from app.models.user import User
from app.schemas.analytics import AnalyticsOut, DashboardStats
from app.services import analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get("/dashboard", response_model=DashboardStats)
def dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Organization-scoped engagement analytics (cached in Redis when available)."""
    return analytics_service.get_dashboard_stats(db, current_user)


@router.get("/posts/{post_id}", response_model=AnalyticsOut)
def post_analytics(
    post_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    analytics = analytics_service.get_post_analytics(db, current_user, post_id)
    if not analytics:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Analytics not found for this post (publish it first)",
        )
    return analytics
