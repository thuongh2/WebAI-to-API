# src/schemas/request.py
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

class GeminiModels(str, Enum):
    """
    Available Gemini models — names must match gemini-webapi's internal model list.
    """

    # Gemini 2.0 Series
    EXP_ADVANCED = "gemini-2.0-exp-advanced"
    FLASH_2_0 = "gemini-2.0-flash-exp"

    # Gemini 1.5 Series
    PRO_1_5 = "gemini-1.5-pro"
    FLASH_1_5 = "gemini-1.5-flash"


class GeminiRequest(BaseModel):
    message: str
    model: GeminiModels = Field(default=GeminiModels.FLASH_2_0, description="Model to use for Gemini.")
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
