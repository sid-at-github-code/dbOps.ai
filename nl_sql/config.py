"""
NL-to-SQL settings — reads from environment / .env file.
All DB and LLM credentials live here.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class NlSqlSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # LLM
    openai_api_key: str = ""
    openrouter_api_key: str = ""
    llm_model: str = "openai/gpt-4o-mini"

    # PostgreSQL — individual params OR a full URI (URI takes precedence)
    supabase_uri: str = ""
    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = ""
    db_user: str = ""
    db_password: str = ""

    # Public API (v1)
    v1_api_key: str = ""       # empty = dev mode, auth skipped
    v1_plan_tier: str = "pro"  # free | basic | pro | enterprise


settings = NlSqlSettings()
