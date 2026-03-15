from __future__ import annotations

import logging

from slack_sdk.web.async_client import AsyncWebClient

from app.config import settings

logger = logging.getLogger(__name__)


class SlackService:
    def __init__(self):
        self.default_client = AsyncWebClient(token=settings.SLACK_BOT_TOKEN)

    def _get_client(self, bot_token: str | None = None) -> AsyncWebClient:
        if bot_token:
            return AsyncWebClient(token=bot_token)
        return self.default_client

    async def reply_to_thread(
        self,
        channel: str,
        thread_ts: str,
        text: str,
        bot_token: str | None = None,
    ):
        client = self._get_client(bot_token)
        await client.chat_postMessage(
            channel=channel,
            thread_ts=thread_ts,
            text=text,
        )

    async def notify_lawyer(self, review_request, ai_review):
        text = (
            f"📋 *새로운 법률 검토 요청*\n\n"
            f"*요청 ID:* `{review_request.id}`\n"
            f"*원본 메시지:*\n> {review_request.original_message[:500]}\n\n"
            f"*AI 검토 결과:*\n{ai_review.content[:1000]}\n\n"
            f"API를 통해 승인 또는 반려해주세요.\n"
            f"`POST /api/v1/reviews/{review_request.id}/approve`"
        )
        await self.default_client.chat_postMessage(
            channel=settings.LAWYER_NOTIFICATION_CHANNEL,
            text=text,
        )


slack_service = SlackService()
