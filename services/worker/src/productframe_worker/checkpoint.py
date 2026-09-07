"""Durable LangGraph checkpoint storage backed by PostgreSQL."""
from contextlib import contextmanager
from typing import Iterator

import psycopg
from langgraph.checkpoint.postgres import PostgresSaver

from productframe_api.config import get_settings


def _psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


@contextmanager
def postgres_checkpointer() -> Iterator[PostgresSaver]:
    """Open a durable checkpointer and ensure its tables exist."""
    connection = psycopg.connect(_psycopg_url(get_settings().database_url), autocommit=True)
    try:
        checkpointer = PostgresSaver(connection)
        checkpointer.setup()
        yield checkpointer
    finally:
        connection.close()
