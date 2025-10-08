"""Connection manager for Clickhouse"""

import threading
from typing import ClassVar, Optional

from attrs import define
from ._client import Client
from ._env import get_dsn


@define
class Manager:
    """Central manager for Clickhouse connection."""

    _instance: ClassVar[Optional[Client]] = None
    _lock: ClassVar[threading.RLock] = threading.RLock()

    @classmethod
    def get_clickhouse(cls) -> Client:
        """
        Returns a thread-safe singleton instance of the DataLoader client for
        ClickHouse.

        Initializes the client if it does not already exist using environment
        variables and the singleton instance of the S3 client.

        Returns:
            DataLoader: The singleton instance of the ClickHouse DataLoader.
        """
        if cls._instance is None:
            with cls._lock:
                cls._instance = Client(get_dsn())
        return cls._instance

    @classmethod
    def close(cls):
        """
        Gracefully closes initialized Clickhouse connections if it exists.
        """
        if cls._instance:
            cls._instance.close()
            cls._instance = None
