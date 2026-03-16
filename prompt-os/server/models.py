from pydantic import BaseModel, Field
from typing import Optional

class PromptCreate(BaseModel):
    prompt:      str
    platform:    str
    url:         Optional[str] = None
    captured_at: str
    session_id:  Optional[str] = None

class RatingUpdate(BaseModel):
    rating:      int = Field(..., ge=1, le=5)
    rating_note: Optional[str] = None

class TemplateCreate(BaseModel):
    title:     str
    category:  str
    template:  str
    variables: Optional[str] = None
    source_id: Optional[int] = None
