import pytest

import app.database.supabase as supabase_module


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
