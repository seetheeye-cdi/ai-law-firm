import logging

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from slack_bolt.adapter.starlette.async_handler import AsyncSlackRequestHandler
from slack_bolt.async_app import AsyncApp

from app.api.routes import clients, health, reviews
from app.config import settings
from app.slack.handlers import register_slack_handlers
from app.web.routes import router as web_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

# Slack Bolt app
slack_app = AsyncApp(
    token=settings.SLACK_BOT_TOKEN,
    signing_secret=settings.SLACK_SIGNING_SECRET,
)
register_slack_handlers(slack_app)
slack_handler = AsyncSlackRequestHandler(slack_app)

# FastAPI app
app = FastAPI(title="AI Law Firm", version="0.1.0")

app.include_router(health.router)
app.include_router(reviews.router)
app.include_router(clients.router)
app.include_router(web_router)


@app.get("/")
async def root():
    return RedirectResponse("/web/dashboard")


@app.post("/slack/events")
async def slack_events(req: Request):
    return await slack_handler.handle(req)
