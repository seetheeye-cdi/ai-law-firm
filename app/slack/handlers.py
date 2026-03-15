import logging
import re

from slack_bolt.async_app import AsyncApp
from sqlalchemy import select

from app.database import async_session
from app.models.models import Client
from app.services.review_service import review_service

logger = logging.getLogger(__name__)


def register_slack_handlers(slack_app: AsyncApp):
    @slack_app.event("app_mention")
    async def handle_mention(event, say):
        team_id = event.get("team")
        channel = event.get("channel")
        thread_ts = event.get("thread_ts") or event.get("ts")
        message_ts = event.get("ts")
        user_id = event.get("user")
        text = event.get("text", "")

        # Remove bot mention from text
        text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

        if not text:
            await say(
                text="법률 검토가 필요한 내용을 멘션과 함께 작성해주세요.",
                thread_ts=thread_ts,
            )
            return

        async with async_session() as db:
            result = await db.execute(
                select(Client).where(
                    Client.slack_team_id == team_id,
                    Client.is_active.is_(True),
                )
            )
            client = result.scalar_one_or_none()

            if not client:
                await say(
                    text="등록되지 않은 워크스페이스입니다. 관리자에게 문의해주세요.",
                    thread_ts=thread_ts,
                )
                return

            from app.services.slack_service import slack_service
            await slack_service.send_review_pending(
                channel, thread_ts, bot_token=client.slack_bot_token,
            )

            try:
                await review_service.process_review_request(
                    db=db,
                    client=client,
                    channel=channel,
                    thread_ts=thread_ts,
                    message_ts=message_ts,
                    user_id=user_id,
                    text=text,
                )
            except Exception:
                logger.exception("Failed to process review request for team %s", team_id)
                await say(
                    text="⚠️ 법률 검토 처리 중 오류가 발생했습니다. 관리자에게 문의해주세요.",
                    thread_ts=thread_ts,
                )
