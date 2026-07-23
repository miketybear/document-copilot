from supabase import AsyncClient, create_async_client

from app.config import settings

_anon_client: AsyncClient | None = None
_service_role_client: AsyncClient | None = None


async def get_anon_client() -> AsyncClient:
    """Anon-scoped client, used only to validate a browser-issued user token."""
    global _anon_client
    if _anon_client is None:
        _anon_client = await create_async_client(settings.supabase_url, settings.supabase_anon_key)
    return _anon_client


async def get_service_role_client() -> AsyncClient:
    """Admin client for privileged writes. Backend-only — never expose this key to the browser."""
    global _service_role_client
    if _service_role_client is None:
        _service_role_client = await create_async_client(settings.supabase_url, settings.supabase_service_role_key)
    return _service_role_client
