from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.review_service import ReviewService


@pytest.mark.asyncio
async def test_process_review_request_success(db_session, seed_client):
    service = ReviewService()

    mock_claude_result = {
        "content": "## 요약\n테스트 검토 결과",
        "model_used": "claude-sonnet-4-20250514",
        "input_tokens": 50,
        "output_tokens": 100,
    }

    with (
        patch("app.services.review_service.claude_service") as mock_claude,
        patch("app.services.review_service.slack_service") as mock_slack,
    ):
        mock_claude.generate_legal_review = AsyncMock(return_value=mock_claude_result)
        mock_slack.send_review_complete = AsyncMock()
        mock_slack.notify_lawyer = AsyncMock()

        await service.process_review_request(
            db=db_session,
            client=seed_client,
            channel="C12345",
            thread_ts="111.222",
            message_ts="111.222",
            user_id="U12345",
            text="계약서 검토 요청",
        )

        mock_claude.generate_legal_review.assert_called_once_with("계약서 검토 요청")
        mock_slack.send_review_complete.assert_called_once()
        mock_slack.notify_lawyer.assert_called_once()


@pytest.mark.asyncio
async def test_process_review_request_claude_error(db_session, seed_client):
    service = ReviewService()

    with (
        patch("app.services.review_service.claude_service") as mock_claude,
        patch("app.services.review_service.slack_service") as mock_slack,
    ):
        mock_claude.generate_legal_review = AsyncMock(side_effect=Exception("API Error"))
        mock_slack.reply_to_thread = AsyncMock()

        await service.process_review_request(
            db=db_session,
            client=seed_client,
            channel="C12345",
            thread_ts="111.222",
            message_ts="111.222",
            user_id="U12345",
            text="계약서 검토 요청",
        )

        # Should post error message to thread
        mock_slack.reply_to_thread.assert_called_once()
        call_args = mock_slack.reply_to_thread.call_args
        assert "오류" in call_args.kwargs.get("text", call_args.args[2] if len(call_args.args) > 2 else "")
