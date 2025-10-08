"""Clickhouse DSN resolution."""

import os
from dotenv import load_dotenv

load_dotenv(override=True)


def get_dsn() -> str:
    """Fetch the ClickHouse DSN from environment variables."""
    dsn = os.getenv("CLICKHOUSE_DSN")
    if not dsn:
        raise EnvironmentError(
            "Missing CLICKHOUSE_DSN in environment. "
            "Please set it in your .env file or system environment."
        )
    return dsn
