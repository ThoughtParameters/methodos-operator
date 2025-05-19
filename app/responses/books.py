from pydantic import BaseModel
from typing import Optional, List, Dict, Any

from app.models.books import Metadata

class UploadResponse(BaseModel):
    """
    Represents the response returned after a book is uploaded.
    """
    message: str
    book_key: str
    metadata: Metadata
    server_info: Dict[str, Any]
    