# Shared job model and queue keys.
from dataclasses import dataclass, asdict, field
import json
import time
import uuid

QUEUE_KEY = "jobs:queue"
DLQ_KEY = "jobs:dlq"
STATUS_PREFIX = "jobs:status:"
IDEMPOTENCY_PREFIX = "jobs:idem:"
MAX_ATTEMPTS = 5


@dataclass
class Job:
    payload: dict
    idempotency_key: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    attempts: int = 0
    created_at: float = field(default_factory=time.time)

    def to_json(self) -> str:
        return json.dumps(asdict(self))

    @staticmethod
    def from_json(raw: str) -> "Job":
        return Job(**json.loads(raw))
