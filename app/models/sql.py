from sqlmodel import SQLModel, Field
from typing import Optional, List
from uuid import UUID

class BaseModel(SQLModel):
    id: Optional[int] = Field(default=None, primary_key=True)
    
class Agent(BaseModel, table=True):
    __tablename__ = "agents"
    
    fqdn: str = Field(index=True, nullable=False)
    type: str = Field(index=True, nullable=False)
    public_key: bytes = Field(index=True, nullable=False)
    private_key: bytes = Field(index=True, nullable=False)
    version: str = Field(index=True, nullable=False)
    state: str = Field(index=True, nullable=False)