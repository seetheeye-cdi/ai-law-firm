from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_root_redirect(client):
    response = await client.get("/", follow_redirects=False)
    assert response.status_code == 307
    assert "/web/dashboard" in response.headers["location"]


@pytest.mark.asyncio
async def test_login_page(client):
    # With dev mode (no auth), login redirects to dashboard
    response = await client.get("/web/login", follow_redirects=False)
    assert response.status_code == 302


@pytest.mark.asyncio
async def test_login_invalid_key(client):
    response = await client.post(
        "/web/login",
        data={"api_key": "wrong-key"},
        follow_redirects=False,
    )
    assert response.status_code == 401
    assert "Invalid" in response.text


@pytest.mark.asyncio
async def test_login_success(client, api_headers):
    response = await client.post(
        "/web/login",
        data={"api_key": "test-api-key"},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "/web/dashboard" in response.headers["location"]
    assert "lawyer_session" in response.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_dashboard_accessible(client, seed_review):
    response = await client.get("/web/dashboard")
    assert response.status_code == 200
    assert "Dashboard" in response.text


@pytest.mark.asyncio
async def test_review_detail_page(client, seed_review):
    client.cookies.set("lawyer_session", "test-api-key")
    response = await client.get(f"/web/reviews/{seed_review.id}")
    assert response.status_code == 200
    assert "AI 검토 결과" in response.text


@pytest.mark.asyncio
async def test_approve_via_web(client, seed_review):
    client.cookies.set("lawyer_session", "test-api-key")

    with patch("app.services.review_service.slack_service") as mock_slack:
        mock_slack.send_review_result = AsyncMock()

        response = await client.post(
            f"/web/reviews/{seed_review.id}/approve",
            data={
                "final_content": "Legal review complete. No issues found.",
                "notes": "Test note",
            },
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "Approved" in response.headers["location"]
        mock_slack.send_review_result.assert_called_once()


@pytest.mark.asyncio
async def test_reject_via_web(client, seed_review):
    client.cookies.set("lawyer_session", "test-api-key")

    with patch("app.services.review_service.slack_service") as mock_slack:
        mock_slack.send_rejection = AsyncMock()

        response = await client.post(
            f"/web/reviews/{seed_review.id}/reject",
            data={"notes": "Needs more analysis", "final_content": ""},
            follow_redirects=False,
        )
        assert response.status_code == 302
        assert "Rejected" in response.headers["location"]


@pytest.mark.asyncio
async def test_reject_without_notes(client, seed_review):
    client.cookies.set("lawyer_session", "test-api-key")

    response = await client.post(
        f"/web/reviews/{seed_review.id}/reject",
        data={"notes": "", "final_content": ""},
        follow_redirects=False,
    )
    assert response.status_code == 302
    assert "required" in response.headers["location"]
