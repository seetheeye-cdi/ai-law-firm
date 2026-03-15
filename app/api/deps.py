from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

api_key_header = APIKeyHeader(name="X-API-Key")


async def get_session() -> AsyncSession:
    async for session in get_db():
        yield session


async def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if api_key == settings.API_KEY:
        return api_key
    lawyer_keys = settings.get_lawyer_keys()
    if api_key in lawyer_keys:
        return api_key
    raise HTTPException(status_code=403, detail="Invalid API key")


async def verify_lawyer_api_key(api_key: str = Security(api_key_header)) -> str:
    """Verify API key and return the associated lawyer ID."""
    lawyer_keys = settings.get_lawyer_keys()
    if api_key in lawyer_keys:
        return lawyer_keys[api_key]
    if api_key == settings.API_KEY:
        return "admin"
    raise HTTPException(status_code=403, detail="Invalid API key")
