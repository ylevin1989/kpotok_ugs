from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    project_name: str = "content-factory"
    env: str = "development"
    database_url: str
    redis_url: str = "redis://localhost:6379/0"
    cf_app_url: str = "http://localhost:3100"
    cf_api_url: str = "http://localhost:8100"
    hermes_base_url: str = "https://ha.uno-ai.pw"
    jwt_secret: str = "change_me"
    worker_token: str = "change_me_worker"
    worker_lease_seconds: int = 300
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 10080
    s3_endpoint: str = 'http://127.0.0.1:9000'
    s3_access_key: str = 'minio'
    s3_secret_key: str = 'change_me'
    s3_bucket: str = 'content-factory'
    s3_region: str = 'us-east-1'
    s3_use_ssl: bool = False

    @model_validator(mode="after")
    def validate_runtime_secrets(self) -> "Settings":
        if self.env.lower() in {"production", "staging"} and self.jwt_secret == "change_me":
            raise ValueError("jwt_secret must be explicitly set outside test/development envs")
        if self.env.lower() in {"production", "staging"} and self.worker_token == "change_me_worker":
            raise ValueError("worker_token must be explicitly set outside test/development envs")
        return self

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
