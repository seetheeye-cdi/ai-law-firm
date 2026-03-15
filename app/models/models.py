import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    slack_team_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    slack_team_name: Mapped[str] = mapped_column(String(255))
    slack_bot_token: Mapped[str] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    review_requests: Mapped[List["ReviewRequest"]] = relationship(back_populates="client")


class ReviewRequest(Base):
    __tablename__ = "review_requests"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    client_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clients.id"))
    slack_channel_id: Mapped[str] = mapped_column(String(64))
    slack_thread_ts: Mapped[str] = mapped_column(String(64))
    slack_message_ts: Mapped[str] = mapped_column(String(64))
    slack_user_id: Mapped[str] = mapped_column(String(64))
    original_message: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), default="pending")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now()
    )

    client: Mapped["Client"] = relationship(back_populates="review_requests")
    ai_review: Mapped[Optional["AIReview"]] = relationship(
        back_populates="review_request", uselist=False
    )
    lawyer_review: Mapped[Optional["LawyerReview"]] = relationship(
        back_populates="review_request", uselist=False
    )


class AIReview(Base):
    __tablename__ = "ai_reviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    review_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("review_requests.id"), unique=True
    )
    content: Mapped[str] = mapped_column(Text)
    model_used: Mapped[str] = mapped_column(String(64))
    input_tokens: Mapped[Optional[int]] = mapped_column(nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    review_request: Mapped["ReviewRequest"] = relationship(back_populates="ai_review")


class LawyerReview(Base):
    __tablename__ = "lawyer_reviews"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    review_request_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("review_requests.id"), unique=True
    )
    lawyer_id: Mapped[str] = mapped_column(String(128))
    final_content: Mapped[str] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(32))
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    review_request: Mapped["ReviewRequest"] = relationship(
        back_populates="lawyer_review"
    )
