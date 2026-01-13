from pydantic import BaseModel, Field
from typing import List, Optional

# --- Request Schemas (Data coming IN) ---

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="The user's query")
    session_id: Optional[str] = Field(None, description="Unique ID for conversation history")

class UploadResponse(BaseModel):
    filename: str
    status: str
    message: str

# --- Response Schemas (Data going OUT) ---
# (Optional: useful if we want structured JSON responses later instead of streams)
class ChatResponse(BaseModel):
    answer: str
    citations: List[str] = []