from pydantic import BaseModel
from datetime import datetime, timedelta

from typing import Optional

from app.models.agent import AgentConfiguration

import pytz

class AgentConfigurationResponse(BaseModel):
    generated_at: datetime = datetime.now(tz=pytz.UTC)
    expires: datetime = datetime.now(tz=pytz.UTC) + timedelta.seconds(3600)
    configuration: Optional[AgentConfiguration]
)