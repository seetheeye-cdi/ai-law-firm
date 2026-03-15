"""Seed a test Client so the Slack bot can look up the workspace."""
import argparse
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import async_session, engine, Base  # noqa: E402
from app.models.models import Client  # noqa: E402
from sqlalchemy import select  # noqa: E402


async def seed(team_id: str, team_name: str, bot_token: str):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as db:
        existing = await db.execute(
            select(Client).where(Client.slack_team_id == team_id)
        )
        if existing.scalar_one_or_none():
            print(f"Client with team_id={team_id} already exists. Skipping.")
            return

        client = Client(
            slack_team_id=team_id,
            slack_team_name=team_name,
            slack_bot_token=bot_token,
        )
        db.add(client)
        await db.commit()
        print(f"Created client: {team_name} (team_id={team_id})")


def main():
    parser = argparse.ArgumentParser(description="Seed development data")
    parser.add_argument("--team-id", required=True, help="Slack Team ID (e.g. T12345ABC)")
    parser.add_argument("--team-name", default="Dev Workspace", help="Workspace name")
    parser.add_argument("--bot-token", default="", help="Bot token (optional, uses env default)")
    args = parser.parse_args()

    bot_token = args.bot_token
    if not bot_token:
        from app.config import settings
        bot_token = settings.SLACK_BOT_TOKEN

    asyncio.run(seed(args.team_id, args.team_name, bot_token))


if __name__ == "__main__":
    main()
