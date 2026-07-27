def test_register_and_login(client):
    reg = client.post(
        "/api/auth/register",
        json={
            "email": "owner@org.example.com",
            "password": "secret123",
            "organization_name": "Org One",
        },
    )
    assert reg.status_code == 200
    assert "access_token" in reg.json()

    login = client.post(
        "/api/auth/login",
        json={"email": "owner@org.example.com", "password": "secret123"},
    )
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {login.json()['access_token']}"})
    assert me.status_code == 200
    assert me.json()["role"] == "admin"
    assert me.json()["email"] == "owner@org.example.com"


def test_member_cannot_create_social_account(client, auth_headers):
    # Admin adds a member
    add = client.post(
        "/api/auth/members",
        headers=auth_headers,
        json={"email": "member@acme.example.com", "password": "secret123", "role": "member"},
    )
    assert add.status_code == 200
    assert add.json()["role"] == "member"

    login = client.post(
        "/api/auth/login",
        json={"email": "member@acme.example.com", "password": "secret123"},
    )
    member_headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    forbidden = client.post(
        "/api/social-accounts",
        headers=member_headers,
        json={
            "platform": "instagram",
            "account_name": "@member",
            "access_token": "tok",
        },
    )
    assert forbidden.status_code == 403


def test_invalid_login(client, auth_headers):
    response = client.post(
        "/api/auth/login",
        json={"email": "admin@acme.example.com", "password": "wrong-password"},
    )
    assert response.status_code == 401
