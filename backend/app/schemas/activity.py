from datetime import datetime

from pydantic import BaseModel


class OrderActivityOut(BaseModel):
    id: str
    type: str
    title: str
    description: str = ""
    actor: str = ""
    created_at: datetime
