from pydantic import BaseModel

# Pydantic model for document update
class DocumentUpdate(BaseModel):
    filename: str = None
    source_language: str = None
    translation_status: str = None
    chars_per_word: float = None

# Pydantic model for document metadata
class DocumentMetadata(BaseModel):
    id: int
    filename: str
    mime_type: str