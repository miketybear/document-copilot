import truststore

# Must run before anything else opens an SSL context: on-prem MCP servers are frequently behind
# a corporate CA that isn't in the bundled certifi trust store but is in the OS's — swapping in
# the OS-native store here fixes verification for every outbound HTTPS call in the process, not
# just the ones this app makes directly.
truststore.inject_into_ssl()

from fastapi import FastAPI  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402

from app.api import chat, mcp, me  # noqa: E402
from app.config import settings  # noqa: E402

app = FastAPI(title="Document Copilot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(me.router)
app.include_router(chat.router)
app.include_router(mcp.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
