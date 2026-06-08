"""Pydantic models for the calling service."""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    username: str
    phone_number: str


class UserCreate(BaseModel):
    username: str
    phone_number: str


class UserUpdate(BaseModel):
    username: Optional[str] = None
    phone_number: Optional[str] = None


class CommunicationLog(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    recipient_name: str
    recipient_phone: str
    action: str           # "call" or "sms"
    message: str
    status: str           # "success" or "failed"
    sid: Optional[str] = None


class CommandRequest(BaseModel):
    command: str
