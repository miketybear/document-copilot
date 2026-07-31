import pytest

import app.database.supabase as supabase_module
from app.database.supabase import get_service_role_client


@pytest.fixture(autouse=True)
def _reset_supabase_client_cache():
    """Each test gets its own asyncio event loop (pytest-asyncio, function scope), but the
    app's Supabase clients are cached at module level for the process's lifetime — reusing a
    client whose httpx transport was opened in a different (now-closed) event loop breaks."""
    supabase_module._anon_client = None
    supabase_module._service_role_client = None
    yield
    supabase_module._anon_client = None
    supabase_module._service_role_client = None


@pytest.fixture
async def cleanup_rows():
    """Integration tests that insert real rows register their ids here; deletes run in FK-safe
    order (chunks -> documents -> groups) regardless of test outcome, so a real Supabase project
    used for testing doesn't accumulate throwaway rows."""
    ids: dict[str, list[str]] = {"document_chunks": [], "source_documents": [], "document_groups": []}
    yield ids
    client = await get_service_role_client()
    for table in ("document_chunks", "source_documents", "document_groups"):
        table_ids = ids[table]
        if table_ids:
            await client.table(table).delete().in_("id", table_ids).execute()
