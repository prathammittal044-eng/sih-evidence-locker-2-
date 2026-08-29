from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional

class User(BaseModel):
    id: int
    username: str
    role: str

    class Config:
        from_attributes = True

class DocumentVersion(BaseModel):
    id: int
    version_number: int
    status: str
    file_path: str
    file_hash: str
    created_at: datetime
    uploaded_by: int
    extracted_text: Optional[str] = None
    ai_summary: Optional[str] = None
    entities: Optional[str] = None

    class Config:
        from_attributes = True

class Document(BaseModel):
    id: int
    name: str
    doc_type: str
    created_at: datetime
    versions: List[DocumentVersion] = []

    class Config:
        from_attributes = True

class CaseBase(BaseModel):
    case_number: str
    title: str

class CaseCreate(CaseBase):
    pass

class Case(CaseBase):
    id: int
    status: str
    is_sealed: bool = False
    sealed_by: Optional[int] = None
    sealed_at: Optional[datetime] = None
    created_at: datetime
    documents: List[Document] = []

    class Config:
        from_attributes = True

class AuditLog(BaseModel):
    id: int
    user_id: int
    action: str
    details: str
    timestamp: datetime

    class Config:
        from_attributes = True

