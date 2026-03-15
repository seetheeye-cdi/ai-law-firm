import uuid
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel


# --- Client ---
class ClientCreate(BaseModel):
    slack_team_id: str
    slack_team_name: str
    slack_bot_token: str


class ClientResponse(BaseModel):
    id: uuid.UUID
    slack_team_id: str
    slack_team_name: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


# --- AI Review ---
class AIReviewResponse(BaseModel):
    id: uuid.UUID
    content: str
    model_used: str
    input_tokens: Optional[int]
    output_tokens: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# --- Lawyer Review ---
class LawyerReviewResponse(BaseModel):
    id: uuid.UUID
    lawyer_id: str
    final_content: str
    decision: str
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class ApproveRequest(BaseModel):
    final_content: str
    notes: Optional[str] = None


class RejectRequest(BaseModel):
    notes: str


# --- Review Request ---
class ReviewRequestSummary(BaseModel):
    id: uuid.UUID
    client: ClientResponse
    original_message: str
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReviewRequestDetail(ReviewRequestSummary):
    slack_channel_id: str
    slack_thread_ts: str
    slack_user_id: str
    ai_review: Optional[AIReviewResponse] = None
    lawyer_review: Optional[LawyerReviewResponse] = None


# --- Pagination ---
class PaginatedResponse(BaseModel):
    items: List[ReviewRequestSummary]
    total: int
    page: int
    size: int
