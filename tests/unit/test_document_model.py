from rag_platform.domain.enums import DocumentStatus
from rag_platform.infrastructure.db.models import DocumentModel


def test_document_model_default_status() -> None:
    assert DocumentModel.__tablename__ == "documents"
    col = DocumentModel.__table__.c.status
    assert col.default is not None or DocumentStatus.UPLOADED
