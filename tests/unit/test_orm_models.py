from rag_platform.infrastructure.db.models import KnowledgeBaseModel, OrganizationModel


def test_orm_models_tablenames() -> None:
    assert OrganizationModel.__tablename__ == "organizations"
    assert KnowledgeBaseModel.__tablename__ == "knowledge_bases"
