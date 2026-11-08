"""ARQ worker entrypoint."""

from arq import run_worker

from rag_platform.workers.settings import WorkerSettings


def main() -> None:
    run_worker(WorkerSettings)


if __name__ == "__main__":
    main()
