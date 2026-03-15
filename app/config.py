from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    DATABASE_URL: str
    SLACK_SIGNING_SECRET: str
    SLACK_BOT_TOKEN: str
    LAWYER_NOTIFICATION_CHANNEL: str
    ANTHROPIC_API_KEY: str
    API_KEY: str
    LAWYER_API_KEYS: str = ""  # JSON: {"api_key": "lawyer_name", ...}

    model_config = SettingsConfigDict(env_file=".env")

    def get_lawyer_keys(self) -> dict[str, str]:
        if not self.LAWYER_API_KEYS:
            return {}
        import json
        return json.loads(self.LAWYER_API_KEYS)


settings = Settings()
