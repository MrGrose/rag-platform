from arq import cron
from arq.connections import RedisSettings

from rag_platform.config import get_settings
from rag_platform.workers.outbox_dispatcher import dispatch_outbox_events
from rag_platform.workers.tasks import (
    delete_document_vectors,
    noop,
    process_document,
    recover_stale_documents,
    recover_stale_evaluations,
    reindex_document,
    run_evaluation,
    worker_shutdown,
)


class WorkerSettings:
    functions = [
        dispatch_outbox_events,
        noop,
        process_document,
        delete_document_vectors,
        reindex_document,
        run_evaluation,
        recover_stale_documents,
        recover_stale_evaluations,
        worker_shutdown,
    ]
    cron_jobs = [
        cron(dispatch_outbox_events, second=0),
        cron(recover_stale_documents, minute={0, 15, 30, 45}),
        cron(recover_stale_evaluations, minute={5, 20, 35, 50}),
    ]
    on_shutdown = worker_shutdown
    redis_settings = RedisSettings.from_dsn(str(get_settings().arq_redis_url))
