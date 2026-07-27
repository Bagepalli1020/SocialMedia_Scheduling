from tests.helpers import future_time


def test_data_isolation_between_organizations(
    client, auth_headers, second_org_headers, social_account_id
):
    # Org A creates a post
    create = client.post(
        "/api/posts",
        headers=auth_headers,
        json={
            "content": "Org A secret post",
            "scheduled_time": future_time(90),
            "social_account_id": social_account_id,
        },
    )
    assert create.status_code == 201
    post_id = create.json()["id"]

    # Org B cannot see Org A posts
    list_b = client.get("/api/posts", headers=second_org_headers)
    assert list_b.status_code == 200
    assert all(p["id"] != post_id for p in list_b.json())

    # Org B cannot fetch Org A post by id
    get_b = client.get(f"/api/posts/{post_id}", headers=second_org_headers)
    assert get_b.status_code == 404

    # Org B cannot see Org A social accounts
    accounts_b = client.get("/api/social-accounts", headers=second_org_headers)
    assert accounts_b.status_code == 200
    assert all(a["id"] != social_account_id for a in accounts_b.json())

    # Analytics for Org B start empty / isolated
    dash_b = client.get("/api/analytics/dashboard", headers=second_org_headers)
    assert dash_b.status_code == 200
    assert dash_b.json()["total_posts"] == 0
