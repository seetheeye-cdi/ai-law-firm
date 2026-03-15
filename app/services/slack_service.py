from __future__ import annotations

import logging
import re

from slack_sdk.web.async_client import AsyncWebClient

from app.config import settings

logger = logging.getLogger(__name__)


def md_to_slack(text: str) -> str:
    """Convert Markdown to Slack mrkdwn format."""
    lines = text.split("\n")
    result = []
    for line in lines:
        # ## Header → *Header*
        line = re.sub(r"^#{1,3}\s+(.+)$", r"*\1*", line)
        # **bold** → *bold*
        line = re.sub(r"\*\*(.+?)\*\*", r"*\1*", line)
        result.append(line)
    return "\n".join(result)


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
        blocks: list | None = None,
        bot_token: str | None = None,
    ):
        client = self._get_client(bot_token)
        kwargs = dict(channel=channel, thread_ts=thread_ts, text=text)
        if blocks:
            kwargs["blocks"] = blocks
        await client.chat_postMessage(**kwargs)

    async def send_review_result(
        self,
        channel: str,
        thread_ts: str,
        lawyer_id: str,
        final_content: str,
        bot_token: str | None = None,
    ):
        """Send approved review result to Slack thread with Block Kit."""
        slack_content = md_to_slack(final_content)
        # Truncate for Slack block limit (3000 chars)
        if len(slack_content) > 2800:
            slack_content = slack_content[:2800] + "\n\n_(전체 내용은 대시보드에서 확인하세요)_"

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "⚖️ 법률 검토 완료", "emoji": True},
            },
            {
                "type": "context",
                "elements": [
                    {"type": "mrkdwn", "text": f"담당 변호사: *{lawyer_id}*"},
                ],
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": slack_content},
            },
        ]
        await self.reply_to_thread(
            channel, thread_ts,
            text=f"⚖️ 법률 검토 완료 - {lawyer_id}",
            blocks=blocks,
            bot_token=bot_token,
        )

    async def send_review_pending(
        self,
        channel: str,
        thread_ts: str,
        bot_token: str | None = None,
    ):
        """Send 'review in progress' message."""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "🔍 *법률 검토를 시작합니다.*\n잠시만 기다려주세요...",
                },
            },
        ]
        await self.reply_to_thread(
            channel, thread_ts,
            text="🔍 법률 검토를 시작합니다.",
            blocks=blocks,
            bot_token=bot_token,
        )

    async def send_review_complete(
        self,
        channel: str,
        thread_ts: str,
        bot_token: str | None = None,
    ):
        """Send 'AI review done, waiting for lawyer' message."""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "✅ *AI 법률 검토가 완료되었습니다.*\n담당 변호사 확인 후 최종 의견을 드리겠습니다.",
                },
            },
        ]
        await self.reply_to_thread(
            channel, thread_ts,
            text="✅ AI 법률 검토가 완료되었습니다.",
            blocks=blocks,
            bot_token=bot_token,
        )

    async def send_rejection(
        self,
        channel: str,
        thread_ts: str,
        lawyer_id: str,
        notes: str,
        bot_token: str | None = None,
    ):
        """Send rejection notice to Slack thread."""
        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"📌 *추가 검토가 필요합니다.*\n\n"
                        f"담당 변호사 *{lawyer_id}* 님이 추가 검토를 진행합니다.\n"
                        f"별도로 연락드리겠습니다."
                    ),
                },
            },
        ]
        await self.reply_to_thread(
            channel, thread_ts,
            text=f"📌 추가 검토가 필요합니다 - {lawyer_id}",
            blocks=blocks,
            bot_token=bot_token,
        )

    async def notify_lawyer(self, review_request, ai_review):
        """Send lawyer notification with Block Kit."""
        dashboard_url = f"{settings.BASE_URL}/web/reviews/{review_request.id}"
        summary = md_to_slack(ai_review.content[:800])

        blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "📋 새로운 법률 검토 요청", "emoji": True},
            },
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*원본 메시지:*\n> {review_request.original_message[:300]}",
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*AI 검토 요약:*\n{summary}",
                },
            },
            {"type": "divider"},
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "🔗 대시보드에서 검토하기", "emoji": True},
                        "url": dashboard_url,
                        "style": "primary",
                    },
                ],
            },
        ]
        await self.default_client.chat_postMessage(
            channel=settings.LAWYER_NOTIFICATION_CHANNEL,
            text=f"📋 새로운 법률 검토 요청 - {review_request.original_message[:50]}",
            blocks=blocks,
        )


slack_service = SlackService()
