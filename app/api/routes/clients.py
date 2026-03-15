from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_session, verify_api_key
from app.models.models import Client
from app.schemas.schemas import ClientCreate, ClientResponse

router = APIRouter(prefix="/api/v1/clients", dependencies=[Depends(verify_api_key)])


@router.post("", response_model=ClientResponse, status_code=201)
async def create_client(
    body: ClientCreate,
    db: AsyncSession = Depends(get_session),
):
    client = Client(
        slack_team_id=body.slack_team_id,
        slack_team_name=body.slack_team_name,
        slack_bot_token=body.slack_bot_token,
    )
    db.add(client)
    await db.commit()
    await db.refresh(client)
    return ClientResponse.model_validate(client)


@router.get("", response_model=List[ClientResponse])
async def list_clients(
    db: AsyncSession = Depends(get_session),
):
    result = await db.execute(select(Client).order_by(Client.created_at.desc()))
    return [ClientResponse.model_validate(c) for c in result.scalars().all()]
