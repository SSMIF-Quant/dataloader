"""Clickhouse data loader"""

from typing import Any, Dict, List, Optional, ClassVar

import pandas as pd
from attrs import define

from ._manager import Manager
from ._client import Client


@define
class DataLoader:
    """
    A unified data loader for ClickHouse tables and materialized views.

    Supports:
        - dynamic column selection
        - filters and parameters
        - table/view aliasing
    """

    database: ClassVar[str] = "ssmif_quant"
    client: ClassVar[Client] = Manager.get_connection()

    @classmethod
    def query(
        cls,
        source: str,
        columns_list: Optional[List[str]] = None,
        column_pattern: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> pd.DataFrame:
        """
        Fetch data from Clickhouse with flexibile configuration.

        Priority order:
            1. view (materialized)
            2. base table
        """
        query = cls._build_query(
            source, columns_list, column_pattern, filters, limit, offset
        )

        params = {}
        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    params[key] = tuple(value)
                else:
                    params[key] = value

        df = cls.client.query(query, params)
        return cls._format_dataframe(df)

    @staticmethod
    def _format_dataframe(df: pd.DataFrame) -> pd.DataFrame:
        """
        Standardizes and cleans ClickHouse query output.
        Handles:
        - datetime conversion
        - sorting & deduplication
        - renaming columns (for single or multiple symbols)
        - setting Date as index
        """
        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"])
            df = df.rename(columns={"date": "Date"})

        if "symbol" in df.columns:
            df = df.sort_values(["symbol", "Date"]).drop_duplicates(
                subset=["symbol", "Date"]
            )
            df.set_index("Date", inplace=True)

            renamed_frames = []
            for sym, group in df.groupby("symbol"):
                group = group.drop(columns="symbol")
                group = group.rename(
                    columns=lambda c: (
                        f"{sym}_{c}" if c != "Date" else c
                    )  # pylint: disable=W0640
                )
                renamed_frames.append(group)

            df = pd.concat(renamed_frames, axis=1).sort_index()

        else:
            df = df.sort_values("Date").drop_duplicates(subset=["Date"])
            df.set_index("Date", inplace=True)

        return df

    @staticmethod
    def _rename_columns(symbol: str, df: pd.DataFrame) -> pd.DataFrame:
        """
        Renames columns to a standard format.
        """
        df = df.rename(columns=lambda col: f"{symbol}_{col}")
        return df

    @classmethod
    def _build_query(
        cls,
        source: str,
        columns_list: Optional[List[str]] = None,
        column_pattern: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        select_expr = cls._resolve_columns(source, columns_list, column_pattern)

        query = f"SELECT {select_expr} FROM {source} WHERE 1=1"

        if filters:
            for key, value in filters.items():
                if key == "start":
                    query += f" AND date >= %({key})s"
                elif key == "end":
                    query += f" AND date <= %({key})s"
                else:
                    if isinstance(value, list):
                        query += f" AND {key} IN %({key})s"
                    else:
                        query += f" AND {key} = %({key})s"

        query += " ORDER BY date"

        if limit:
            if offset:
                query += f" LIMIT {offset}, {limit}"
            else:
                query += f" LIMIT {limit}"

        return query

    @staticmethod
    def _resolve_columns(
        source: str,
        columns_list: Optional[List[str]] = None,
        column_pattern: Optional[List[str]] = None,
    ) -> str:
        """
        Combine multiple column selection methods:
            - explicit column list
            - dynamic patterns

        Returns a Clickhouse SELECT expression.
        """
        selected_cols: list[str] = ["date"]

        if source == "equities":
            selected_cols.append("symbol")

        if columns_list:
            selected_cols.extend(columns_list)

        if column_pattern:
            for p in column_pattern:
                selected_cols.append(f"COLUMNS('{p}')")

        return ", ".join(selected_cols)

    @classmethod
    def tables(cls) -> List[str]:
        """
        Returns available tables.
        """
        query = f"SHOW TABLES FROM {cls.database}"
        df = cls.client.query(query)
        return df["name"].tolist()

    @classmethod
    def fields(cls, source: str) -> List[str]:
        """
        Returns all columns for a given table.
        """
        query = f"SHOW COLUMNS FROM {cls.database}.{source}"
        df = cls.client.query(query)
        return df["field"].tolist()

    @classmethod
    def all(cls, source: str) -> pd.DataFrame:
        """Fetch entire table."""
        raise NotImplementedError

    @classmethod
    def columns(cls, source: str) -> pd.DataFrame:
        """Select specific columns from source."""
        raise NotImplementedError

    @classmethod
    def head(cls, source: str, n: int = 10) -> pd.DataFrame:
        """Get first N rows."""
        raise NotImplementedError

    @classmethod
    def paginate(cls, source: str, limit: int, offset: int) -> pd.DataFrame:
        """Get paginated results."""
        raise NotImplementedError

    @classmethod
    def filter(cls, source: str, **kwargs) -> pd.DataFrame:
        """
        Simple equality filters. Pass column=value pairs.

        Example:
            DataLoader.filter('equities', symbol='AAPL', date_start='2024-01-01')
        """
        raise NotImplementedError

    @classmethod
    def match_pattern(cls, source: str, pattern: str) -> List[str]:
        """Get columns matching a pattern."""
        raise NotImplementedError

    @classmethod
    def select_pattern(cls, source: str, pattern: str, **filters) -> pd.DataFrame:
        """Select columns matching a pattern with optional filters."""
        raise NotImplementedError

    @classmethod
    def date_range(
        cls, source: str, start_date: str, end_date: str, **additional_filters
    ) -> pd.DataFrame:
        """Get data between two dates (YYYY-MM-DD format)."""
        raise NotImplementedError

    @classmethod
    def first_date(cls, source: str) -> pd.Timestamp:
        """Return the earliest date in the table."""
        raise NotImplementedError

    @classmethod
    def last_date(cls, source: str) -> pd.Timestamp:
        """Return the latest date in the table."""
        raise NotImplementedError

    @classmethod
    def latest(cls, source: str, n: int = 1) -> pd.DataFrame:
        """Return the last N rows per symbol or table."""
        raise NotImplementedError

    @classmethod
    def describe(cls, source: str) -> pd.DataFrame:
        """Return column types, non-null counts, basic stats."""
        raise NotImplementedError

    @classmethod
    def column_types(cls, source: str) -> Dict[str, str]:
        """Return data types for each column in a table."""
        raise NotImplementedError

    @classmethod
    def stream(cls, source: str, batch_size: int = 10000):
        """
        Yield data in chunks of batch_size.
        Example usage:
            for df_chunk in DataLoader.stream('equities', 5000):
                process(df_chunk)
        """
        raise NotImplementedError

    @classmethod
    def iter_chunks(cls, source: str, chunk_size: int = 10000):
        """Alias for stream."""
        return cls.stream(source, batch_size=chunk_size)

    @classmethod
    def batch_query(cls, sources: List[str], filters: Optional[Dict[str, Any]] = None):
        """Query multiple tables or symbols in a single call."""
        raise NotImplementedError
