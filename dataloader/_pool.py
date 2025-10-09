"""Clickhouse connection pool for multi-thread applications."""

from contextlib import contextmanager
from typing import Optional, Union

import clickhouse_connect
from attrs import define, field
from urllib3.poolmanager import PoolManager, ProxyManager
from clickhouse_connect.driver import httputil


class PoolError(Exception):
    "A generic exception that may be raised."


@define
class Pool:
    """A connection pool for clickhouse, akin to psycopg2."""

    _dsn: str
    _maxsize: Optional[int] = field(default=16)
    _num_pools: Optional[int] = field(default=12)
    _pool_mgr: Optional[Union[PoolManager, ProxyManager]] = field(default=None)
    _closed: Optional[bool] = field(default=False)

    def __attrs_post_init__(self):
        self._pool_mgr = httputil.get_pool_manager(
            maxsize=self._maxsize, num_pools=self._num_pools
        )

    @contextmanager
    def get_client(self):
        """Get a lightweight client using the shared HTTP pool."""

        if self._closed:
            raise PoolError("ClickHouse pool is closed")

        client = clickhouse_connect.get_client(pool_mgr=self._pool_mgr, dsn=self._dsn)
        try:
            yield client
        finally:
            pass

    def cleanup(self):
        """
        Close all underlying HTTP connections.
        Should be called when the application exits.
        """
        if self._closed:
            return
        self._pool_mgr.clear()
        self._closed = True
