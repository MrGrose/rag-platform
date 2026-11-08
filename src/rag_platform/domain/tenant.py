from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True, slots=True)
class TenantContext:
    organization_id: UUID
    api_key_id: UUID | None
    scopes: tuple[str, ...]
    auth_mode: str

    @property
    def is_open_dev(self) -> bool:
        return self.auth_mode == "open_dev"
