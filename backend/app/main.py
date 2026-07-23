from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import me
from app.config import settings

app = FastAPI(title="Document Copilot")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(me.router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
