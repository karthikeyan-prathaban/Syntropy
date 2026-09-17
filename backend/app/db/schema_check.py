from __future__ import annotations

import logging
from pathlib import Path

from sqlalchemy import inspect

from app.core.config import get_settings
from app.db.session import engine

logger = logging.getLogger(__name__)

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


def _head_revision() -> str | None:
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    try:
        config = Config(str(ALEMBIC_INI))
        config.set_main_option("script_location", str(ALEMBIC_INI.parent / "alembic"))
        return ScriptDirectory.from_config(config).get_current_head()
    except Exception:
        logger.debug("Could not read the Alembic head revision", exc_info=True)
        return None


def _inspect(connection) -> tuple[bool, str | None]:
    inspector = inspect(connection)
    tables = set(inspector.get_table_names())
    if "alembic_version" not in tables:
        return bool(tables), None
    row = connection.exec_driver_sql("SELECT version_num FROM alembic_version").fetchone()
    return True, row[0] if row else None


async def verify_schema() -> None:
    """Confirm the database has been migrated before serving traffic.

    Without this, an unmigrated database surfaces as a 500 on every endpoint with
    a bare "no such table" buried in the traceback.
    """
    async with engine.connect() as conn:
        has_tables, current = await conn.run_sync(_inspect)

    head = _head_revision()
    settings = get_settings()

    if current is None:
        message = (
            "The database has no schema. Migrations are the only schema path.\n"
            f"  Run: cd backend && alembic upgrade head\n"
            f"  Database: {settings.database_url}"
        )
        if settings.is_production or not has_tables:
            raise RuntimeError(message)
        logger.error(message)
        return

    if head and current != head:
        message = (
            f"Database is at migration {current} but the code expects {head}.\n"
            "  Run: cd backend && alembic upgrade head"
        )
        if settings.is_production:
            raise RuntimeError(message)
        logger.warning(message)
        return

    logger.info("Database schema is up to date (migration %s)", current)
