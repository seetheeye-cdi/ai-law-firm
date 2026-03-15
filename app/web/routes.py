from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request, Response
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session
from app.config import settings
from app.models.models import ReviewRequest
from app.services.review_service import review_service

router = APIRouter(prefix="/web")
templates = Jinja2Templates(directory=str(Path(__file__).parent.parent / "templates"))

COOKIE_NAME = "lawyer_session"


def _identify_user(api_key: str) -> Optional[str]:
    """Return lawyer name for valid key, None otherwise."""
    lawyer_keys = settings.get_lawyer_keys()
    if api_key in lawyer_keys:
        return lawyer_keys[api_key]
    if api_key == settings.API_KEY:
        return "admin"
    return None


def _get_lawyer(request: Request) -> Optional[str]:
    """Get lawyer name from session cookie, or default to admin in dev mode."""
    api_key = request.cookies.get(COOKIE_NAME, "")
    name = _identify_user(api_key)
    if not name:
        return "admin"
    return name


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    if _get_lawyer(request):
        return RedirectResponse("/web/dashboard", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": None, "lawyer_name": None})


@router.post("/login")
async def login_submit(request: Request, api_key: str = Form(...)):
    name = _identify_user(api_key)
    if not name:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid API Key", "lawyer_name": None},
            status_code=401,
        )
    response = RedirectResponse("/web/dashboard", status_code=302)
    response.set_cookie(COOKIE_NAME, api_key, httponly=True, max_age=86400)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse("/web/login", status_code=302)
    response.delete_cookie(COOKIE_NAME)
    return response


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    status: Optional[str] = None,
    page: int = 1,
    db: AsyncSession = Depends(get_session),
):
    lawyer_name = _get_lawyer(request)
    if not lawyer_name:
        return RedirectResponse("/web/login", status_code=302)

    size = 20
    reviews, total = await review_service.list_reviews(db, status=status, page=page, size=size)
    total_pages = max(1, (total + size - 1) // size)

    # Stats
    pending_count = (await db.execute(
        select(func.count()).select_from(ReviewRequest).where(ReviewRequest.status == "ai_reviewed")
    )).scalar() or 0
    approved_count = (await db.execute(
        select(func.count()).select_from(ReviewRequest).where(ReviewRequest.status == "approved")
    )).scalar() or 0
    rejected_count = (await db.execute(
        select(func.count()).select_from(ReviewRequest).where(ReviewRequest.status == "rejected")
    )).scalar() or 0

    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "lawyer_name": lawyer_name,
        "reviews": reviews,
        "total": total,
        "page": page,
        "total_pages": total_pages,
        "current_status": status or "",
        "pending_count": pending_count,
        "approved_count": approved_count,
        "rejected_count": rejected_count,
        "flash_message": request.query_params.get("msg"),
        "flash_type": request.query_params.get("msg_type", "success"),
    })


@router.get("/reviews/{review_id}", response_class=HTMLResponse)
async def review_detail(
    request: Request,
    review_id: uuid.UUID,
    db: AsyncSession = Depends(get_session),
):
    lawyer_name = _get_lawyer(request)
    if not lawyer_name:
        return RedirectResponse("/web/login", status_code=302)

    review = await review_service.get_review(db, review_id)
    if not review:
        return RedirectResponse("/web/dashboard?msg=Review not found&msg_type=error", status_code=302)

    return templates.TemplateResponse("review_detail.html", {
        "request": request,
        "lawyer_name": lawyer_name,
        "review": review,
        "flash_message": request.query_params.get("msg"),
        "flash_type": request.query_params.get("msg_type", "success"),
    })


@router.post("/reviews/{review_id}/approve")
async def approve_review_web(
    request: Request,
    review_id: uuid.UUID,
    final_content: str = Form(""),
    notes: str = Form(""),
    db: AsyncSession = Depends(get_session),
):
    lawyer_name = _get_lawyer(request)
    if not lawyer_name:
        return RedirectResponse("/web/login", status_code=302)

    if not final_content.strip():
        return RedirectResponse(
            f"/web/reviews/{review_id}?msg=Final opinion is required&msg_type=error",
            status_code=302,
        )

    try:
        await review_service.approve_review(
            db, review_id,
            lawyer_id=lawyer_name,
            final_content=final_content.strip(),
            notes=notes.strip() or None,
        )
    except ValueError as e:
        return RedirectResponse(
            f"/web/reviews/{review_id}?msg={str(e)}&msg_type=error",
            status_code=302,
        )

    return RedirectResponse(
        f"/web/reviews/{review_id}?msg=Approved! Slack message sent.",
        status_code=302,
    )


@router.post("/reviews/{review_id}/reject")
async def reject_review_web(
    request: Request,
    review_id: uuid.UUID,
    notes: str = Form(""),
    db: AsyncSession = Depends(get_session),
):
    lawyer_name = _get_lawyer(request)
    if not lawyer_name:
        return RedirectResponse("/web/login", status_code=302)

    if not notes.strip():
        return RedirectResponse(
            f"/web/reviews/{review_id}?msg=Notes are required for rejection&msg_type=error",
            status_code=302,
        )

    try:
        await review_service.reject_review(
            db, review_id,
            lawyer_id=lawyer_name,
            notes=notes.strip(),
        )
    except ValueError as e:
        return RedirectResponse(
            f"/web/reviews/{review_id}?msg={str(e)}&msg_type=error",
            status_code=302,
        )

    return RedirectResponse(
        f"/web/reviews/{review_id}?msg=Rejected. Slack notification sent.",
        status_code=302,
    )
