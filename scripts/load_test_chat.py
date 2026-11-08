import argparse
import asyncio
import time
from uuid import UUID

import httpx


async def _one(client: httpx.AsyncClient, kb_id: UUID, question: str) -> int:
    response = await client.post(
        "/v1/chat",
        json={"knowledge_base_id": str(kb_id), "question": question},
    )
    return response.status_code


async def run(*, base_url: str, kb_id: UUID, concurrency: int, requests: int) -> None:
    started = time.perf_counter()
    async with httpx.AsyncClient(base_url=base_url, timeout=60.0) as client:
        sem = asyncio.Semaphore(concurrency)

        async def task(i: int) -> int:
            async with sem:
                return await _one(client, kb_id, f"load-test-{i % 50}")

        results = await asyncio.gather(*(task(i) for i in range(requests)))
    elapsed = time.perf_counter() - started
    ok = sum(1 for code in results if code == 200)
    print(f"requests={requests} ok={ok} elapsed_s={elapsed:.2f} rps={requests / elapsed:.2f}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--knowledge-base-id", required=True, type=UUID)
    parser.add_argument("--concurrency", type=int, default=4)
    parser.add_argument("--requests", type=int, default=20)
    args = parser.parse_args()
    asyncio.run(
        run(
            base_url=args.base_url,
            kb_id=args.knowledge_base_id,
            concurrency=args.concurrency,
            requests=args.requests,
        ),
    )


if __name__ == "__main__":
    main()
