"""Clickhouse client connection"""

import socket
from typing import Any, Optional, Dict

from attrs import define
from clickhouse_connect.driver.exceptions import (
    ClickHouseError,
    DatabaseError,
    DataError,
)

from ._pool import Pool


@define
class Client:
    """Client for interacting with the ClickHouse database."""

    dsn: str
    pool: Optional[Pool] = None

    def __attrs_post_init__(self) -> None:
        """Connects to ClickHouse."""
        self._connect()
        self.health()

    def _connect(self) -> None:
        """Establishes a connection to ClickHouse."""
        if self.pool is None:
            try:
                self.pool = Pool(dsn=self.dsn)
                return
            except (DatabaseError, ClickHouseError, DataError, socket.error) as e:
                raise RuntimeError from e

    def close(self) -> None:
        """Closes the ClickHouse client connection."""
        if self.pool is None:
            raise RuntimeError
        try:
            self.pool.cleanup()
            self.pool = None
        except (ClickHouseError, DatabaseError) as e:
            raise RuntimeError from e

    def health(self) -> bool:
        """
        Checks the health of both ClickHouse and S3 clients.

        Returns:
            bool: True if both services are healthy, False otherwise.
        """
        if self.pool is None:
            raise RuntimeError
        try:
            with self.pool.get_client() as client:
                result = client.query("SELECT 1")
                rows = result.result_rows
                return bool(rows and rows[0][0] == 1)
        except (  # pylint: disable=W0718
            Exception,
            DatabaseError,
            ClickHouseError,
            DataError,
        ) as e:
            raise RuntimeError from e

    def query(self, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a query against a pool of clients."""
        if not self.pool:
            raise RuntimeError("ClickHouse pool not available")
        with self.pool.get_client() as client:
            return client.query_df(sql, params)
