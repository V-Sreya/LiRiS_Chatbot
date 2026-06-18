import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from app.api.endpoints import router as api_router
from app.api.sources import router as sources_router, ws_router as sources_ws_router
from app.core.config import settings
from app.core.database import init_db
from app.dependencies import get_session_id
import asyncio

app = FastAPI(title="Manus Chatbot", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")
app.include_router(sources_router, prefix="/api/v1")
app.include_router(sources_ws_router)


@app.get("/")
async def root():
    return {"message": "Manus Chatbot Backend - Ready", "docs": "/docs"}


@app.on_event("startup")
async def startup():
    await init_db()
    print("✅ Database initialized")

    # One-time cleanup: the legacy "products" Chroma collection used to hold
    # seeded ShopWave demo data. Drop it on startup so it doesn't shadow
    # answers from ingested URLs or uploaded documents.
    try:
        import chromadb

        client = chromadb.PersistentClient(path=settings.CHROMA_DB_PATH)
        existing = {c.name for c in client.list_collections()}
        if settings.COLLECTION_NAME in existing:
            client.delete_collection(settings.COLLECTION_NAME)
            print(f"✅ Removed legacy collection: {settings.COLLECTION_NAME}")
    except Exception as e:
        print(f"⚠️ Legacy collection cleanup skipped: {e}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)
