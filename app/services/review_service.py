from __future__ import annotations

import logging
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.models import AIReview, Client, LawyerReview, ReviewRequest
from app.services.claude_service import claude_service
from app.services.slack_service import slack_service

logger = logging.getLogger(__name__)


class ReviewService:
    async def process_review_request(
        self,
        db: AsyncSession,
        client: Client,
        channel: str,
        thread_ts: str,
        message_ts: str,
        user_id: str,
        text: str,
    ):
        review_request = ReviewRequest(
            client_id=client.id,
            slack_channel_id=channel,
            slack_thread_ts=thread_ts or message_ts,
            slack_message_ts=message_ts,
            slack_user_id=user_id,
            original_message=text,
            status="pending",
        )
        db.add(review_request)
        await db.flush()

        try:
            result = await claude_service.generate_legal_review(text)
        except Exception:
            logger.exception("Claude API call failed for request %s", review_request.id)
            review_request.status = "error"
            await db.commit()
            await slack_service.reply_to_thread(
                channel,
                thread_ts or message_ts,
                "⚠️ 법률 검토 중 오류가 발생했습니다. 잠시 후 다시 시도해주세요.",
                bot_token=client.slack_bot_token,
            )
            return

        ai_review = AIReview(
            review_request_id=review_request.id,
            content=result["content"],
            model_used=result["model_used"],
            input_tokens=result["input_tokens"],
            output_tokens=result["output_tokens"],
        )
        db.add(ai_review)
        review_request.status = "ai_reviewed"
        await db.commit()

        await slack_service.send_review_complete(
            channel,
            thread_ts or message_ts,
            bot_token=client.slack_bot_token,
        )
        await slack_service.notify_lawyer(review_request, ai_review)

    async def list_reviews(
        self,
        db: AsyncSession,
        status: str | None = None,
        client_id: uuid.UUID | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[ReviewRequest], int]:
        query = select(ReviewRequest).options(selectinload(ReviewRequest.client))
        count_query = select(func.count()).select_from(ReviewRequest)

        if status:
            query = query.where(ReviewRequest.status == status)
            count_query = count_query.where(ReviewRequest.status == status)
        if client_id:
            query = query.where(ReviewRequest.client_id == client_id)
            count_query = count_query.where(ReviewRequest.client_id == client_id)

        total = (await db.execute(count_query)).scalar()
        query = (
            query.order_by(ReviewRequest.created_at.desc())
            .offset((page - 1) * size)
            .limit(size)
        )
        result = await db.execute(query)
        return result.scalars().all(), total

    async def get_review(
        self, db: AsyncSession, review_id: uuid.UUID
    ) -> ReviewRequest | None:
        query = (
            select(ReviewRequest)
            .options(
                selectinload(ReviewRequest.client),
                selectinload(ReviewRequest.ai_review),
                selectinload(ReviewRequest.lawyer_review),
            )
            .where(ReviewRequest.id == review_id)
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()

    async def approve_review(
        self,
        db: AsyncSession,
        review_id: uuid.UUID,
        lawyer_id: str,
        final_content: str,
        notes: str | None = None,
    ) -> ReviewRequest:
        review_request = await self.get_review(db, review_id)
        if not review_request:
            raise ValueError("Review request not found")
        if review_request.status != "ai_reviewed":
            raise ValueError(f"Cannot approve review with status: {review_request.status}")

        lawyer_review = LawyerReview(
            review_request_id=review_id,
            lawyer_id=lawyer_id,
            final_content=final_content,
            decision="approved",
            notes=notes,
        )
        db.add(lawyer_review)
        review_request.status = "approved"
        await db.commit()
        await db.refresh(review_request)

        client = review_request.client
        await slack_service.send_review_result(
            review_request.slack_channel_id,
            review_request.slack_thread_ts,
            lawyer_id=lawyer_id,
            final_content=final_content,
            bot_token=client.slack_bot_token,
        )
        return await self.get_review(db, review_id)

    async def reject_review(
        self,
        db: AsyncSession,
        review_id: uuid.UUID,
        lawyer_id: str,
        notes: str,
    ) -> ReviewRequest:
        review_request = await self.get_review(db, review_id)
        if not review_request:
            raise ValueError("Review request not found")
        if review_request.status != "ai_reviewed":
            raise ValueError(f"Cannot reject review with status: {review_request.status}")

        lawyer_review = LawyerReview(
            review_request_id=review_id,
            lawyer_id=lawyer_id,
            final_content="",
            decision="rejected",
            notes=notes,
        )
        db.add(lawyer_review)
        review_request.status = "rejected"
        await db.commit()
        await db.refresh(review_request)

        client = review_request.client
        await slack_service.send_rejection(
            review_request.slack_channel_id,
            review_request.slack_thread_ts,
            lawyer_id=lawyer_id,
            notes=notes,
            bot_token=client.slack_bot_token,
        )
        return await self.get_review(db, review_id)


review_service = ReviewService()
