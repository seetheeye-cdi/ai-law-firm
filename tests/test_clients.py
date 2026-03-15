import pytest


@pytest.mark.asyncio
async def test_create_client(client, api_headers):
    response = await client.post(
        "/api/v1/clients",
        json={
            "slack_team_id": "T_NEW",
            "slack_team_name": "New Workspace",
            "slack_bot_token": "xoxb-new-token",
        },
        headers=api_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["slack_team_id"] == "T_NEW"
    assert data["is_active"] is True


@pytest.mark.asyncio
async def test_create_client_no_auth(client):
    response = await client.post(
        "/api/v1/clients",
        json={
            "slack_team_id": "T_FAIL",
            "slack_team_name": "Fail",
            "slack_bot_token": "xoxb-fail",
        },
    )
    assert response.status_code in (401, 403)


@pytest.mark.asyncio
async def test_list_clients(client, api_headers, seed_client):
    response = await client.get("/api/v1/clients", headers=api_headers)
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["slack_team_id"] == "T12345"
