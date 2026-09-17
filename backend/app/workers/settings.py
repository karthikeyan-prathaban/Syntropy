from arq import cron
from arq.connections import RedisSettings

from app.core.config import get_settings
from app.core.logging import apply_zero_leakage_logging
from app.workers.tasks import (
    enforce_retention,
    enrich_user_job,
    nightly_enrichment,
    parse_statement_job,
    refresh_all_consents,
    refresh_consent_job,
)


async def startup(_ctx) -> None:
    apply_zero_leakage_logging()


class WorkerSettings:
    """arq worker. Run with: arq app.workers.settings.WorkerSettings"""

    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
    functions = [parse_statement_job, refresh_consent_job, enrich_user_job]
    cron_jobs = [
        # Twice daily AA pull, offset from the hour to avoid the thundering herd.
        cron(refresh_all_consents, hour={3, 15}, minute=17),
        cron(nightly_enrichment, hour=4, minute=5),
        cron(enforce_retention, hour=5, minute=30),
    ]
    on_startup = startup
    max_jobs = 10
    job_timeout = 600
    keep_result = 3600
