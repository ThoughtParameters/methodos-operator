from pydantic import BaseModel, Field
from typing import List, Optional
from uuid import UUID
from datetime import datetime
from app.enums import State, Type, Mode

class MethodosAgent(BaseModel):
    fqdn: str = Field(
        description="Hostname of the node the agent is running on.",
        example="host.example.com"
    )
    uuid: UUID = Field(
        description="Unique identifier for the agent.",
        example="123e4567-e89b-12d3-a456-426614174000"
    ) 
    type: Type = Field(
        description="The agent type either host, container, or unknown.",
        example=Type.HOST,
    )
    state: State = Field(
        description="The agent state either active, inactive, or unknown.",
        example=State.ACTIVE,
    )
    mode: Mode = Field(
        description="The agent mode either enforcing or monitoring.",
        example=Mode.ENFORCING,
    )
    version: str = Field(
        description="The agent version.",
        example="1.0.0",
    )
    uptime: int = Field(
        description="The agent uptime in seconds.",
        example=1000,
    )
    cert: bytes = Field(
        description="The public certificate of the agent.",
        example=b"""-----BEGIN CERTIFICATE-----
        ...
        -----END CERTIFICATE-----
        """,
    )

class RegisterAgent(BaseModel):
    fqdn: str = Field(
        description="Hostname of the node the agent is running on.",
        example="host.example.com"
    )
    uuid: UUID = Field(
        description="Unique identifier for the agent.",
        example="123e4567-e89b-12d3-a456-426614174000"
    )
    type: Type = Field(
        description="The agent type either host, container, or unknown.",
        example=Type.HOST,
    )
    version: str = Field(
        description="The agent version.",
        example="1.0.0",
    )
    