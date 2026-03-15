from unittest.mock import AsyncMock, patch

import pytest


@pytest.mark.asyncio
async def test_list_reviews(client, api_headers, seed_review):
    response = await client.get("/api/v1/reviews", headers=api_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1


@pytest.mark.asyncio
async def test_list_reviews_filter_status(client, api_headers, seed_review):
    response = await client.get(
        "/api/v1/reviews", params={"status": "ai_reviewed"}, headers=api_headers
    )
    assert response.status_code == 200
    assert response.json()["total"] >= 1

    response = await client.get(
        "/api/v1/reviews", params={"status": "pending"}, headers=api_headers
    )
    assert response.status_code == 200
    assert response.json()["total"] == 0


@pytest.mark.asyncio
async def test_get_review_detail(client, api_headers, seed_review):
    response = await client.get(
        f"/api/v1/reviews/{seed_review.id}", headers=api_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ai_reviewed"
    assert data["ai_review"] is not None
    assert data["lawyer_review"] is None


@pytest.mark.asyncio
async def test_get_review_not_found(client, api_headers):
    import uuid

    response = await client.get(
        f"/api/v1/reviews/{uuid.uuid4()}", headers=api_headers
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_approve_review(client, api_headers, seed_review):
    with patch("app.services.review_service.slack_service") as mock_slack:
        mock_slack.send_review_result = AsyncMock()

        response = await client.post(
            f"/api/v1/reviews/{seed_review.id}/approve",
            json={
                "final_content": "검토 완료. 법적 문제 없음.",
                "notes": "특이사항 없음",
            },
            headers=api_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["lawyer_review"]["decision"] == "approved"
        assert data["lawyer_review"]["lawyer_id"] == "admin"
        mock_slack.send_review_result.assert_called_once()


@pytest.mark.asyncio
async def test_approve_review_with_lawyer_key(client, lawyer_headers, seed_review):
    with patch("app.services.review_service.slack_service") as mock_slack:
        mock_slack.send_review_result = AsyncMock()

        response = await client.post(
            f"/api/v1/reviews/{seed_review.id}/approve",
            json={"final_content": "검토 완료."},
            headers=lawyer_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["lawyer_review"]["lawyer_id"] == "김변호사"


@pytest.mark.asyncio
async def test_reject_review(client, api_headers, seed_review):
    with patch("app.services.review_service.slack_service") as mock_slack:
        mock_slack.send_rejection = AsyncMock()

        response = await client.post(
            f"/api/v1/reviews/{seed_review.id}/reject",
            json={"notes": "추가 검토 필요"},
            headers=api_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"


@pytest.mark.asyncio
async def test_approve_already_approved(client, api_headers, seed_review):
    with patch("app.services.review_service.slack_service") as mock_slack:
        mock_slack.send_review_result = AsyncMock()

        # First approve
        await client.post(
            f"/api/v1/reviews/{seed_review.id}/approve",
            json={"final_content": "OK"},
            headers=api_headers,
        )

        # Second approve should fail
        response = await client.post(
            f"/api/v1/reviews/{seed_review.id}/approve",
            json={"final_content": "Again"},
            headers=api_headers,
        )
        assert response.status_code == 400
