from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.common import ORMModel


class FaqOut(ORMModel):
    id: UUID
    lang: str
    category: str
    question: str
    answer: str
    position: int
    active: bool
    updated_at: datetime


class FaqIn(BaseModel):
    lang: Literal["uz", "ru"]
    category: str = Field(default="general", min_length=1, max_length=40)
    question: str = Field(min_length=1, max_length=200)
    answer: str = Field(min_length=1, max_length=4000)
    position: int = 0
    active: bool = True
