from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from rag_platform.application.ports.storage import ObjectStorage
from rag_platform.infrastructure.db.session import get_session_factory
from rag_platform.infrastructure.fakes.storage import InMemoryObjectStorage
from rag_platform.infrastructure.storage.s3 import S3ObjectStorage


async def get_db_session() -> AsyncIterator[AsyncSession]:
    factory = get_session_factory()
    session = factory()
    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


def get_object_storage() -> ObjectStorage:
    return S3ObjectStorage()


def get_test_object_storage() -> ObjectStorage:
    return InMemoryObjectStorage()
