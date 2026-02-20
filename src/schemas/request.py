# src/schemas/request.py
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class GeminiModels(str, Enum):
    """
    Available Gemini models (gemini-webapi >= 1.19.2).
    """

    # Gemini 3.0 Series
    PRO = "gemini-3.0-pro"
    FLASH = "gemini-3.0-flash"
    FLASH_THINKING = "gemini-3.0-flash-thinking"


class GeminiRequest(BaseModel):
    message: str
    model: GeminiModels = Field(default=GeminiModels.FLASH, description="Model to use for Gemini.")
    files: Optional[List[str]] = []

class OpenAIChatRequest(BaseModel):
    messages: List[dict]
    model: Optional[GeminiModels] = None
    stream: Optional[bool] = False

class Part(BaseModel):
    text: str

class Content(BaseModel):
    parts: List[Part]

class GoogleGenerativeRequest(BaseModel):
    contents: List[Content]
