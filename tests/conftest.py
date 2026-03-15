import os

# Set environment variables BEFORE any app imports
os.environ.update({
    "DATABASE_URL": "sqlite+aiosqlite:///:memory:",
    "SLACK_SIGNING_SECRET": "test-secret",
    "SLACK_BOT_TOKEN": "xoxb-test-token",
    "LAWYER_NOTIFICATION_CHANNEL": "C_TEST",
    "ANTHROPIC_API_KEY": "sk-ant-test",
    "API_KEY": "test-api-key",
    "LAWYER_API_KEYS": '{"lawyer-key-1": "김변호사"}',
})

from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base

TEST_API_KEY = "test-api-key"

engine = create_async_engine("sqlite+aiosqlite:///:memory:")
TestingSessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest_asyncio.fixture
async def db_session():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with TestingSessionLocal() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client(db_session):
    from app.api.deps import get_session
    from app.main import app

    async def override_get_session():
        yield db_session

    app.dependency_overrides[get_session] = override_get_session
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest.fixture
def api_headers():
    return {"X-API-Key": TEST_API_KEY}


@pytest.fixture
def lawyer_headers():
    return {"X-API-Key": "lawyer-key-1"}


@pytest.fixture
def sample_slack_event():
    return {
        "type": "app_mention",
        "team": "T12345",
        "channel": "C12345",
        "ts": "1234567890.123456",
        "user": "U12345",
        "text": "<@B12345> 이 계약서의 손해배상 조항을 검토해주세요.",
    }


@pytest_asyncio.fixture
async def seed_client(db_session):
    from app.models.models import Client

    c = Client(
        slack_team_id="T12345",
        slack_team_name="Test Workspace",
        slack_bot_token="xoxb-test",
    )
    db_session.add(c)
    await db_session.commit()
    await db_session.refresh(c)
    return c


@pytest_asyncio.fixture
async def seed_review(db_session, seed_client):
    from app.models.models import AIReview, ReviewRequest

    rr = ReviewRequest(
        client_id=seed_client.id,
        slack_channel_id="C12345",
        slack_thread_ts="1234567890.123456",
        slack_message_ts="1234567890.123456",
        slack_user_id="U12345",
        original_message="계약서 검토 요청합니다.",
        status="ai_reviewed",
    )
    db_session.add(rr)
    await db_session.flush()

    ai = AIReview(
        review_request_id=rr.id,
        content="## 요약\nAI 검토 결과입니다.",
        model_used="claude-sonnet-4-20250514",
        input_tokens=100,
        output_tokens=200,
    )
    db_session.add(ai)
    await db_session.commit()
    await db_session.refresh(rr)
    return rr
