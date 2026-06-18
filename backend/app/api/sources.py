import asyncio
import json
import logging

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    WebSocket,
    WebSocketDisconnect,
)

from app.dependencies import get_session_id
from app.models.product import IngestionRequest
from app.services.ingestion import ingestion_service
from app.services.ingestion.url_validator import ValidationError

log = logging.getLogger("sources_api")

router = APIRouter(tags=["sources"])


@router.post("/sources/url", status_code=202)
async def submit_url(
    request: IngestionRequest,
    session_id: str = Depends(get_session_id),
):
    if not request.url or not request.url.strip():
        raise HTTPException(status_code=400, detail="URL is required")
    sid = request.session_id or session_id
    try:
        source_id = await ingestion_service.start(
            url=request.url,
            session_id=sid,
            max_pages=request.max_pages,
            max_depth=request.max_depth,
        )
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {
        "source_id": source_id,
        "status": "queued",
        "ws_url": f"/ws/sources/{source_id}",
    }


@router.get("/sources/{source_id}")
async def get_source(source_id: str):
    status = await ingestion_service.get_status(source_id)
    if not status:
        raise HTTPException(status_code=404, detail="Source not found")
    return status


@router.get("/sources")
async def list_sources(session_id: str = Depends(get_session_id)):
    return {"sources": await ingestion_service.list_for_session(session_id)}


@router.delete("/sources/{source_id}")
async def detach_source(source_id: str):
    result = await ingestion_service.detach(source_id)
    if not result.get("detached"):
        raise HTTPException(status_code=404, detail=result.get("reason", "not_found"))
    return result


ws_router = APIRouter()


@ws_router.websocket("/ws/sources/{source_id}")
async def ws_source_progress(websocket: WebSocket, source_id: str):
    await websocket.accept()
    queue = ingestion_service.get_queue(source_id)
    if queue is None:
        await websocket.send_text(
            json.dumps({"type": "error", "reason": "unknown source_id"})
        )
        await websocket.close()
        return
    try:
        while True:
            event = await queue.get()
            if event is None:
                break
            await websocket.send_text(json.dumps(event.to_dict()))
            if event.type == "complete":
                break
    except WebSocketDisconnect:
        return
    except asyncio.CancelledError:
        return
    finally:
        try:
            await websocket.close()
        except Exception:
            pass
