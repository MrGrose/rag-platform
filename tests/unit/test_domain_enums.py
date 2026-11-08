from rag_platform.domain.enums import DocumentStatus, JobStatus


def test_document_status_values() -> None:
    assert DocumentStatus.READY == "ready"
    assert JobStatus.PENDING == "pending"
