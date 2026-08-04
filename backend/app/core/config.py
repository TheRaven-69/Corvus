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


settings = Settings()
