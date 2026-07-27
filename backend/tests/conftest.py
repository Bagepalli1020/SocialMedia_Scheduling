import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# Force SQLite for tests before app imports engine-dependent modules
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["SECRET_KEY"] = "test-secret-key-for-pytest-only"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"

from app.database import Base, get_db
from app.main import app
from app.models import *  # noqa: F401,F403


@pytest.fixture()
def db_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def client(db_session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture()
def auth_headers(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "admin@acme.example.com",
            "password": "secret123",
            "organization_name": "Acme Corp",
        },
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def second_org_headers(client):
    response = client.post(
        "/api/auth/register",
        json={
            "email": "admin@beta.example.com",
            "password": "secret123",
            "organization_name": "Beta Inc",
        },
    )
    assert response.status_code == 200, response.text
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def social_account_id(client, auth_headers):
    response = client.post(
        "/api/social-accounts",
        headers=auth_headers,
        json={
            "platform": "twitter",
            "account_name": "@acme",
            "access_token": "mock-token-123",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]

