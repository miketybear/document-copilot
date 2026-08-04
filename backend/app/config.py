from functools import cached_property

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_url: str
    supabase_anon_key: str
    supabase_service_role_key: str

    database_url: str

    # Classic Azure OpenAI REST endpoint (bare resource root), as used by the embedding
    # deployment. The chat deployment may need a different endpoint style — verify when
    # wiring up Phase 7, don't assume this one applies to chat too.
    azure_openai_endpoint: str
    azure_openai_api_key: str
    azure_openai_api_version: str
    azure_openai_chat_deployment: str
    azure_openai_embedding_deployment: str
    azure_openai_embedding_dimensions: int

    allowed_origins: str = "http://localhost:5173"

    # Fernet key (32 url-safe base64-encoded bytes) used to encrypt MCP connection credentials
    # (API tokens, OAuth access/refresh tokens) at rest. Generate with
    # `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`.
    mcp_token_encryption_key: str

    # Base URL the backend is reachable at, used to build the OAuth redirect_uri for MCP
    # connections (the authorization server calls back to this backend, not the frontend).
    backend_base_url: str

    @cached_property
    def allowed_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.allowed_origins.split(",") if origin.strip()]

    @cached_property
    def sqlalchemy_database_url(self) -> str:
        """DATABASE_URL with the psycopg3 driver forced, since bare postgresql:// has no default driver here."""
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return self.database_url


settings = Settings()
