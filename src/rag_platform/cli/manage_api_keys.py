import argparse
import asyncio
from datetime import UTC, datetime
from uuid import UUID

from rag_platform.application.security.api_key_hash import generate_api_key, hash_api_key
from rag_platform.config import get_settings
from rag_platform.infrastructure.db.api_key_repository import SqlAlchemyApiKeyRepository
from rag_platform.infrastructure.db.repositories import SqlAlchemyOrganizationRepository
from rag_platform.infrastructure.db.session import session_scope


async def _create(organization_id: UUID, name: str) -> None:
    settings = get_settings()
    if not settings.api_key_hash_pepper.strip():
        raise SystemExit("API_KEY_HASH_PEPPER is required")
    prefix, full_key = generate_api_key()
    key_hash = hash_api_key(full_key, settings.api_key_hash_pepper)
    async with session_scope() as session:
        org_repo = SqlAlchemyOrganizationRepository(session)
        if await org_repo.get_by_id(organization_id) is None:
            raise SystemExit(f"organization not found: {organization_id}")
        repo = SqlAlchemyApiKeyRepository(session)
        record = await repo.create(
            organization_id=organization_id,
            name=name,
            key_prefix=prefix,
            key_hash=key_hash,
            scopes=("*",),
            expires_at=None,
        )
        await session.commit()
    print(f"api_key_id={record.id}")
    print(f"organization_id={organization_id}")
    print(f"api_key={full_key}")


async def _list(organization_id: UUID) -> None:
    async with session_scope() as session:
        rows = await SqlAlchemyApiKeyRepository(session).list_for_organization(organization_id)
    for row in rows:
        print(
            f"{row.id} prefix={row.key_prefix} name={row.name} "
            f"revoked={bool(row.revoked_at)} expires={row.expires_at}",
        )


async def _revoke(key_id: UUID) -> None:
    async with session_scope() as session:
        await SqlAlchemyApiKeyRepository(session).revoke(key_id, datetime.now(tz=UTC))
        await session.commit()
    print(f"revoked {key_id}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage organization API keys")
    sub = parser.add_subparsers(dest="cmd", required=True)
    create = sub.add_parser("create")
    create.add_argument("--organization-id", required=True)
    create.add_argument("--name", default="default")
    list_cmd = sub.add_parser("list")
    list_cmd.add_argument("--organization-id", required=True)
    revoke = sub.add_parser("revoke")
    revoke.add_argument("--key-id", required=True)
    args = parser.parse_args()
    if args.cmd == "create":
        asyncio.run(_create(UUID(args.organization_id), args.name))
    elif args.cmd == "list":
        asyncio.run(_list(UUID(args.organization_id)))
    elif args.cmd == "revoke":
        asyncio.run(_revoke(UUID(args.key_id)))


if __name__ == "__main__":
    main()
