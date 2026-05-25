from fastapi import Header, Depends
from uuid import uuid4
from typing import Annotated


async def get_session_id(
    x_session_id: str | None = Header(None, alias="X-Session-ID")
) -> str:
    """Get or generate session ID."""
    return x_session_id or str(uuid4())
