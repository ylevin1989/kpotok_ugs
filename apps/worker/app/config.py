from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    cf_api_base_url: str = 'http://127.0.0.1:8100'
    worker_token: str = 'change_me_worker'
    worker_id: str = 'cf-worker'
    worker_lease_seconds: int = 300
    worker_poll_seconds: int = 15
    worker_process_stages: str = 'fetch-payload,render-output'
    worker_once_job_id: str | None = None
    worker_once_action: str | None = None
    worker_once_error_message: str | None = None
    s3_endpoint: str = 'http://127.0.0.1:9000'
    s3_access_key: str = 'minio'
    s3_secret_key: str = 'change_me'
    s3_bucket: str = 'content-factory'
    s3_region: str = 'us-east-1'
    s3_use_ssl: bool = False
    openrouter_api_key: str | None = None
    openrouter_base_url: str = 'https://openrouter.ai/api/v1'
    openrouter_model: str = 'openai/gpt-5.4-mini'
    openrouter_site_url: str = 'https://app.uno-ai.pw'
    openrouter_app_name: str = 'content-factory'

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


@lru_cache
def get_settings() -> Settings:
    return Settings()
