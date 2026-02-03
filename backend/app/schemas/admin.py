from pydantic import BaseModel
from typing import List
from uuid import UUID


class BulkAssignRequest(BaseModel):
    issue_ids: List[UUID]
    worker_id: UUID
