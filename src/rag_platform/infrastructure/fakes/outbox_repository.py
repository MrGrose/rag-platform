from uuid import UUID


class InMemoryOutboxRepository:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    async def append(
        self,
        *,
        event_type: str,
        aggregate_id: UUID,
        organization_id: UUID,
        payload: dict[str, str],
    ) -> None:
        self.events.append(
            {
                "event_type": event_type,
                "aggregate_id": aggregate_id,
                "organization_id": organization_id,
                "payload": payload,
            },
        )
