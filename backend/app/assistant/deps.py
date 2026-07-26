from dataclasses import dataclass

from supabase import AsyncClient


@dataclass
class DocumentAgentDeps:
    user_id: str
    thread_id: str
    supabase_client: AsyncClient
