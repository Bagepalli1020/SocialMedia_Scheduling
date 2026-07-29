from datetime import datetime, timedelta, timezone

from app.models.post import Post, PostStatus
from app.workers.tasks import run_publish_due_posts, run_publish_post
from tests.helpers import future_time, past_time


def test_reject_past_scheduled_time(client, auth_headers, social_account_id):
    past = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    response = client.post(
        "/api/posts",
        headers=auth_headers,
        json={
            "content": "Hello world",
            "scheduled_time": past,
            "social_account_id": social_account_id,
        },
    )
    assert response.status_code == 422


def test_create_scheduled_post(client, auth_headers, social_account_id):
    response = client.post(
        "/api/posts",
        headers=auth_headers,
        json={
            "content": "Scheduled content",
            "scheduled_time": future_time(120),
            "social_account_id": social_account_id,
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["status"] == "scheduled"
    assert data["content"] == "Scheduled content"


def test_background_publish_updates_status(client, auth_headers, social_account_id, db_session):
    create = client.post(
        "/api/posts",
        headers=auth_headers,
        json={
            "content": "Publish me now",
            "scheduled_time": future_time(60),
            "social_account_id": social_account_id,
        },
    )
    assert create.status_code == 201
    post_id = create.json()["id"]

    # Make it due
    post = db_session.query(Post).filter(Post.id == post_id).first()
    post.scheduled_time = past_time(1)
    db_session.commit()

    # Force success path by patching publisher inside test via valid token already set
    # Run worker inline (no Celery broker)
    result = run_publish_post(db_session, post_id)
    assert result["result"] in {"published", "retry_scheduled", "failed"}

    db_session.refresh(post)
    assert post.status in {PostStatus.published, PostStatus.scheduled, PostStatus.failed}

    # If random failure happened, force publish with guaranteed success token
    if post.status != PostStatus.published:
        post.status = PostStatus.scheduled
        post.scheduled_time = past_time(1)
        post.retry_count = 0
        post.social_account.access_token = "guaranteed-good-token"
        db_session.commit()

        # Monkeypatch random failure away
        from app.services import publisher

        original = publisher.mock_publish_to_platform

        def always_ok(account, content):
            return publisher.PublishResult(
                success=True,
                platform_post_id="tw_test123",
                response="ok",
                views=100,
                likes=10,
                shares=2,
            )

        publisher.mock_publish_to_platform = always_ok
        try:
            result = run_publish_post(db_session, post_id)
        finally:
            publisher.mock_publish_to_platform = original

        assert result["result"] == "published"
        db_session.refresh(post)
        assert post.status == PostStatus.published

        from app.models.analytics import Analytics
        from app.models.post import PostLog

        logs = db_session.query(PostLog).filter(PostLog.post_id == post_id).all()
        assert any(log.status == "publishing" for log in logs)
        assert any(log.status == "published" for log in logs)
        analytics = db_session.query(Analytics).filter(Analytics.post_id == post_id).first()
        assert analytics is not None
        assert analytics.views >= 0
        assert analytics.likes >= 0
        assert analytics.shares >= 0


def test_prevent_duplicate_publishing(client, auth_headers, social_account_id, db_session):
    from app.services import publisher

    create = client.post(
        "/api/posts",
        headers=auth_headers,
        json={
            "content": "Once only",
            "scheduled_time": future_time(30),
            "social_account_id": social_account_id,
        },
    )
    post_id = create.json()["id"]
    post = db_session.query(Post).filter(Post.id == post_id).first()
    post.scheduled_time = past_time(1)
    db_session.commit()

    original = publisher.mock_publish_to_platform

    def always_ok(account, content):
        return publisher.PublishResult(
            success=True,
            platform_post_id="tw_once",
            response="ok",
            views=50,
            likes=5,
            shares=1,
        )

    publisher.mock_publish_to_platform = always_ok
    try:
        first = run_publish_post(db_session, post_id)
        assert first["result"] == "published"
        second = run_publish_post(db_session, post_id)
        assert second["result"] == "already_published"
    finally:
        publisher.mock_publish_to_platform = original


def test_failed_post_with_invalid_token(client, auth_headers, db_session):
    account = client.post(
        "/api/social-accounts",
        headers=auth_headers,
        json={
            "platform": "linkedin",
            "account_name": "Acme LI",
            "access_token": "invalid",
        },
    )
    account_id = account.json()["id"]
    create = client.post(
        "/api/posts",
        headers=auth_headers,
        json={
            "content": "Will fail",
            "scheduled_time": future_time(10),
            "social_account_id": account_id,
        },
    )
    post_id = create.json()["id"]
    post = db_session.query(Post).filter(Post.id == post_id).first()
    post.scheduled_time = past_time(1)
    db_session.commit()

    # Exhaust retries
    for _ in range(5):
        if post.status == PostStatus.failed:
            break
        post.status = PostStatus.scheduled
        post.scheduled_time = past_time(1)
        db_session.commit()
        run_publish_post(db_session, post_id)
        db_session.refresh(post)

    assert post.status == PostStatus.failed
    assert post.retry_count >= 1


def test_publish_due_posts_batch(client, auth_headers, social_account_id, db_session):
    from app.services import publisher

    ids = []
    for i in range(2):
        create = client.post(
            "/api/posts",
            headers=auth_headers,
            json={
                "content": f"Batch {i}",
                "scheduled_time": future_time(40),
                "social_account_id": social_account_id,
            },
        )
        ids.append(create.json()["id"])
        post = db_session.query(Post).filter(Post.id == ids[-1]).first()
        post.scheduled_time = past_time(2)
    db_session.commit()

    original = publisher.mock_publish_to_platform

    def always_ok(account, content):
        return publisher.PublishResult(
            success=True,
            platform_post_id="batch",
            response="ok",
            views=10,
            likes=1,
            shares=0,
        )

    publisher.mock_publish_to_platform = always_ok
    try:
        summary = run_publish_due_posts(db_session, enqueue=False)
    finally:
        publisher.mock_publish_to_platform = original

    assert summary["due_found"] >= 2
    for post_id in ids:
        post = db_session.query(Post).filter(Post.id == post_id).first()
        assert post.status == PostStatus.published


def test_reclaim_stuck_publishing_posts(client, auth_headers, social_account_id, db_session):
    from app.models.post import PostLog
    from app.workers.tasks import reclaim_stuck_publishing_posts

    create = client.post(
        "/api/posts",
        headers=auth_headers,
        json={
            "content": "Stuck post",
            "scheduled_time": future_time(20),
            "social_account_id": social_account_id,
        },
    )
    post_id = create.json()["id"]
    post = db_session.query(Post).filter(Post.id == post_id).first()
    post.status = PostStatus.publishing
    post.scheduled_time = past_time(5)
    db_session.add(
        PostLog(
            post_id=post_id,
            status="publishing",
            response="Claimed then worker died",
            executed_at=datetime.now(timezone.utc) - timedelta(minutes=5),
        )
    )
    db_session.commit()

    reclaimed = reclaim_stuck_publishing_posts(db_session, older_than_seconds=60)
    assert reclaimed == 1
    db_session.refresh(post)
    assert post.status == PostStatus.scheduled
    logs = db_session.query(PostLog).filter(PostLog.post_id == post_id).all()
    assert any(log.status == "reclaimed" for log in logs)
