from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    CALDAV_URL: str = "https://cd.brendon.net"
    CALDAV_USERNAME: str = ""
    CALDAV_PASSWORD: str = ""
    CALDAV_CALENDAR_NAME: str = "Tasks"

    # Auth
    SESSION_SECRET: str = "change-me"
    AUTH_PASSWORD: str = "change-me"
    AUTH_TOKEN: str = ""  # optional static token (Option C)

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
