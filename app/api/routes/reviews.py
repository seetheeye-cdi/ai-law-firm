import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, verify_api_key, verify_lawyer_api_key
from app.schemas.schemas import (
    ApproveRequest,
    PaginatedResponse,
    RejectRequest,
    ReviewRequestDetail,
    ReviewRequestSummary,
)
from app.services.review_service import review_service

router = APIRouter(prefix="/api/v1/reviews", dependencies=[Depends(verify_api_key)])


@router.get("", response_model=PaginatedResponse)
async def list_reviews(
    status: Optional[str] = None,
    client_id: Optional[uuid.UUID] = None,
    page: int = 1,
    size: int = 20,
    db: AsyncSession = Depends(get_session),
):
    items, total = await review_service.list_reviews(db, status, client_id, page, size)
    return PaginatedResponse(
        items=[ReviewRequestSummary.model_validate(r) for r in items],
        total=total,
        page=page,
        size=size,
    )


@router.get("/{review_id}", response_model=ReviewRequestDetail)
async def get_review(
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    review = await review_service.get_review(db, review_id)
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    return ReviewRequestDetail.model_validate(review)


@router.post("/{review_id}/approve", response_model=ReviewRequestDetail)
async def approve_review(
    review_id: uuid.UUID,
    body: ApproveRequest,
    db: AsyncSession = Depends(get_session),
    lawyer_id: str = Depends(verify_lawyer_api_key),
):
    try:
        review = await review_service.approve_review(
            db, review_id, lawyer_id=lawyer_id, final_content=body.final_content, notes=body.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ReviewRequestDetail.model_validate(review)


@router.post("/{review_id}/reject", response_model=ReviewRequestDetail)
async def reject_review(
    review_id: uuid.UUID,
    body: RejectRequest,
    db: AsyncSession = Depends(get_session),
    lawyer_id: str = Depends(verify_lawyer_api_key),
):
    try:
        review = await review_service.reject_review(
            db, review_id, lawyer_id=lawyer_id, notes=body.notes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return ReviewRequestDetail.model_validate(review)
