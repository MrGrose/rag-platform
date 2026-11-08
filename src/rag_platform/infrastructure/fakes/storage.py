from rag_platform.application.ports.storage import ObjectStorage


class InMemoryObjectStorage(ObjectStorage):
    def __init__(self) -> None:
        self._objects: dict[str, tuple[bytes, str]] = {}

    async def put_object(self, key: str, data: bytes, content_type: str) -> None:
        self._objects[key] = (data, content_type)

    async def get_object(self, key: str) -> bytes:
        return self._objects[key][0]

    async def delete_object(self, key: str) -> None:
        self._objects.pop(key, None)

    async def object_exists(self, key: str) -> bool:
        return key in self._objects
