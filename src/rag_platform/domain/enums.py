from enum import StrEnum


class DocumentStatus(StrEnum):
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class QueryStatus(StrEnum):
    CREATED = "created"
    RETRIEVED = "retrieved"
    COMPLETED = "completed"


class JobStatus(StrEnum):
    PENDING = "pending"


class EvaluationStatus(StrEnum):
    PENDING = "pending"
    ENQUEUE_FAILED = "enqueue_failed"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
