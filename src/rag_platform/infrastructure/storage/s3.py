import asyncio

import boto3
from botocore.client import BaseClient, Config
from botocore.exceptions import ClientError

from rag_platform.application.ports.storage import ObjectStorage
from rag_platform.config import get_settings


def _client() -> BaseClient:
    settings = get_settings()
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name="us-east-1",
        config=Config(s3={"addressing_style": "path"}),
    )


class S3ObjectStorage(ObjectStorage):
    async def put_object(self, key: str, data: bytes, content_type: str) -> None:
        bucket = get_settings().s3_bucket

        def _put() -> None:
            _client().put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)

        await asyncio.to_thread(_put)

    async def get_object(self, key: str) -> bytes:
        bucket = get_settings().s3_bucket

        def _get() -> bytes:
            response = _client().get_object(Bucket=bucket, Key=key)
            body = response["Body"].read()
            return bytes(body)

        return await asyncio.to_thread(_get)

    async def delete_object(self, key: str) -> None:
        bucket = get_settings().s3_bucket

        def _delete() -> None:
            _client().delete_object(Bucket=bucket, Key=key)

        await asyncio.to_thread(_delete)

    async def object_exists(self, key: str) -> bool:
        bucket = get_settings().s3_bucket

        def _head() -> bool:
            try:
                _client().head_object(Bucket=bucket, Key=key)
                return True
            except ClientError as exc:
                if exc.response.get("Error", {}).get("Code") == "404":
                    return False
                raise

        return await asyncio.to_thread(_head)
