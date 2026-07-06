from typing import Any

from pydantic import BaseModel


class CollectionResponse(BaseModel):
    data: list[dict[str, Any]] = []
    next_token: str | None = None
