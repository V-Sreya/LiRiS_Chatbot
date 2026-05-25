from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.ext.asyncio import AsyncAttrs
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class Base(AsyncAttrs, DeclarativeBase):
    pass


class FileUpload(Base):
    __tablename__ = "file_uploads"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    filename: Mapped[str] = mapped_column(String, index=True)
    file_size: Mapped[int] = mapped_column(Integer)
    content_type: Mapped[str] = mapped_column(String(100))
    upload_time: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    content_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    chats: Mapped[List["ChatMessage"]] = relationship(back_populates="file")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    message: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(String(10))
    timestamp: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    file_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("file_uploads.id"), nullable=True
    )

    file: Mapped[Optional["FileUpload"]] = relationship(back_populates="chats")


# Pydantic schemas
class FileUploadCreate(BaseModel):
    session_id: str
    filename: str
    file_size: int
    content_type: str
    content_hash: Optional[str] = None


class ChatMessageCreate(BaseModel):
    session_id: str
    message: str
    role: str
    file_id: Optional[int] = None


class ChatMessageResponse(BaseModel):
    id: int
    session_id: str
    message: str
    role: str
    timestamp: str
    file_id: Optional[int]

    class Config:
        from_attributes = True


class IngestedSource(Base):
    __tablename__ = "ingested_sources"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    session_id: Mapped[str] = mapped_column(String, index=True)
    url: Mapped[str] = mapped_column(Text)
    domain: Mapped[str] = mapped_column(String, index=True)
    status: Mapped[str] = mapped_column(String(20))
    pages_seen: Mapped[int] = mapped_column(Integer, default=0)
    products_indexed: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[Any] = mapped_column(JSON, default=list)
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
