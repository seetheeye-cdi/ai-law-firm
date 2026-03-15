import logging
import re

import aiohttp
from slack_bolt.async_app import AsyncApp
from sqlalchemy import select

from app.database import async_session
from app.models.models import Client
from app.services.file_service import extract_text
from app.services.review_service import review_service

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = (".pdf", ".docx", ".hwp", ".hwpx", ".txt")


async def _download_file(url: str, token: str) -> bytes:
    """Download a file from Slack using bot token."""
    headers = {"Authorization": f"Bearer {token}"}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as resp:
            resp.raise_for_status()
            return await resp.read()


async def _extract_files_text(files: list, token: str) -> list[str]:
    """Download and extract text from Slack file attachments."""
    extracted = []
    for f in files:
        name = f.get("name", "")
        if not any(name.lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS):
            logger.info("Skipping unsupported file: %s", name)
            continue

        url = f.get("url_private_download") or f.get("url_private")
        if not url:
            continue

        try:
            data = await _download_file(url, token)
            text = extract_text(data, name)
            if text and not text.startswith("["):
                extracted.append(f"📎 첨부파일: {name}\n{'─' * 40}\n{text}")
                logger.info("Extracted %d chars from %s", len(text), name)
        except Exception:
            logger.exception("Failed to download/extract file: %s", name)
            extracted.append(f"[파일 다운로드 실패: {name}]")

    return extracted


def register_slack_handlers(slack_app: AsyncApp):
    @slack_app.event("app_mention")
    async def handle_mention(event, say, context):
        logger.info("Slack event received: %s", event)
        team_id = event.get("team") or context.get("team_id")
        channel = event.get("channel")
        thread_ts = event.get("thread_ts") or event.get("ts")
        message_ts = event.get("ts")
        user_id = event.get("user")
        text = event.get("text", "")

        # Remove bot mention from text
        text = re.sub(r"<@[A-Z0-9]+>", "", text).strip()

        # Extract text from attached files
        files = event.get("files", [])
        bot_token = context.get("bot_token") or ""
        file_texts = await _extract_files_text(files, bot_token)

        # Combine message text with file contents
        if file_texts:
            full_text = text + "\n\n" + "\n\n".join(file_texts) if text else "\n\n".join(file_texts)
        else:
            full_text = text

        if not full_text.strip():
            await say(
                text="법률 검토가 필요한 내용을 멘션과 함께 작성해주세요.\n"
                     "텍스트 또는 파일(PDF, DOCX, HWP)을 첨부할 수 있습니다.",
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

            # Show file info in pending message
            file_names = [f.get("name", "") for f in files if any(f.get("name", "").lower().endswith(ext) for ext in SUPPORTED_EXTENSIONS)]
            from app.services.slack_service import slack_service
            if file_names:
                await slack_service.reply_to_thread(
                    channel, thread_ts,
                    text=f"🔍 법률 검토를 시작합니다.",
                    blocks=[
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": (
                                    "🔍 *법률 검토를 시작합니다.*\n"
                                    f"📎 첨부파일 {len(file_names)}건 분석 중...\n"
                                    + "\n".join(f"  • {n}" for n in file_names)
                                ),
                            },
                        },
                    ],
                    bot_token=client.slack_bot_token,
                )
            else:
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
                    text=full_text,
                )
            except Exception:
                logger.exception("Failed to process review request for team %s", team_id)
                await say(
                    text="⚠️ 법률 검토 처리 중 오류가 발생했습니다. 관리자에게 문의해주세요.",
                    thread_ts=thread_ts,
                )
