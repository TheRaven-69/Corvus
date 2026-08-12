from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="CORVUS_",
        extra="ignore",
    )

    app_name: str = "Corvus API"
    debug: bool = False
    database_url: str
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            "http://localhost:5173",
        ]
    )


settings = Settings()
