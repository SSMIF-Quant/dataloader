"""Clickhouse data loader"""

from datetime import datetime
from typing import Any, ClassVar, Dict, List, Optional

import pandas as pd
from attrs import define

from ._manager import Manager
from ._client import Client
from ._fred_yf_client import FredYfClient


@define
class DataLoader:
    """
    A unified data loader for ClickHouse tables and materialized views.

    Also supports data fetching via FRED API and Yahoo Finance

    Supports:
        - dynamic column selection
        - filters and parameters
        - table/view aliasing
    """

    database: ClassVar[str] = "ssmif_quant"
    client: ClassVar[Client] = Manager.get_connection()
    alt_client: ClassVar[FredYfClient] = Manager.get_alt_connection()

    @classmethod
    def query_fred_yf(
        cls,
        macro_tickers: List[str],
        equity_tickers: List[str],
        start_date: str,
        end_date: str,
    ) -> Dict[str, pd.DataFrame]:
        """Fetch macro data from FRED and equity data from yfinance."""
        try:
            datetime.strptime(start_date, "%Y-%m-%d")
            datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as e:
            raise ValueError(
                f"Invalid date format. Use YYYY-MM-DD. Got: {start_date}, {end_date}"
            ) from e

        dfs = {}
        dfs["macro"] = cls.alt_client.fetch_macro_data(
            macro_tickers, start_date, end_date
        )
        dfs["equity"] = cls.alt_client.fetch_equity_data(
            equity_tickers, start_date, end_date
        )

        return dfs

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
        query = f"SELECT * FROM {source}"
        df = cls.client.query(query)
        return cls._format_dataframe(df)

    # added columns here
    @classmethod
    def columns(cls, source: str, columns: List[str]) -> pd.DataFrame:
        """Select specific columns from source."""
        query = f"SELECT {', '.join(columns)} FROM {source}"
        df = cls.client.query(query)
        return cls._format_dataframe(df)

    # QUESTION
    # order by date here?
    @classmethod
    def head(cls, source: str, n: int = 10) -> pd.DataFrame:
        """Get first N rows."""
        query = f"SELECT * FROM {source} LIMIT {n}"
        df = cls.client.query(query)
        return cls._format_dataframe(df)

    # Same question as above
    @classmethod
    def paginate(cls, source: str, limit: int, offset: int) -> pd.DataFrame:
        """Get paginated results."""
        query = f"SELECT * From {source} LIMIT {limit} OFFSET {offset}"
        df = cls.client.query(query)
        return cls._format_dataframe(df)

    @classmethod
    def filter(cls, source: str, **kwargs) -> pd.DataFrame:
        """
        Simple equality filters. Pass column=value pairs.

        Example:
            DataLoader.filter('equities', symbol='AAPL', date_start='2024-01-01')
        """
        symbol = kwargs.pop("symbol", None)
        date_start = kwargs.pop("date_start", None)
        date_end = kwargs.pop("date_end", None)

        filters = {}
        if symbol:
            filters["symbol"] = symbol
        if date_start:
            filters["start"] = date_start
        if date_end:
            filters["end"] = date_end
        filters.update(kwargs)

        query = cls._build_query(source, filters=filters)
        df = cls.client.query(query, params=filters)
        return cls._format_dataframe(df)

    @classmethod
    def match_pattern(cls, source: str, pattern: str) -> List[str]:
        """Get columns matching a pattern."""
        query = f"FROM {source} SELECT COLUMNS('{pattern}')"
        df = cls.client.query(query)
        return df["columns"].tolist()

    @classmethod
    def select_pattern(cls, source: str, pattern: str, **filters) -> pd.DataFrame:
        """Select columns matching a pattern with optional filters."""
        columns = cls.match_pattern(source, pattern)
        query = cls._build_query(source, columns_list=columns, filters=filters)
        df = cls.client.query(query, params=filters)
        return cls._format_dataframe(df)

    @classmethod
    def date_range(
        cls, source: str, start_date: str, end_date: str, **additional_filters
    ) -> pd.DataFrame:
        """Get data between two dates (YYYY-MM-DD format)."""
        filters = {
            "start": start_date,
            "end": end_date,
        }
        filters.update(additional_filters)

        query = cls._build_query(source, filters=filters)
        df = cls.client.query(query, params=filters)
        return cls._format_dataframe(df)

    @classmethod
    def first_date(cls, source: str) -> pd.Timestamp:
        """Return the earliest date in the table."""
        query = f"SELECT MIN(date) AS first_date FROM {source}"
        df = cls.client.query(query)
        return pd.to_datetime(df["first_date"].iloc[0])

    @classmethod
    def last_date(cls, source: str) -> pd.Timestamp:
        """Return the latest date in the table."""
        query = f"SELECT MAX(date) AS last_date FROM {source}"
        df = cls.client.query(query)
        return pd.to_datetime(df["last_date"].iloc[0])

    # want me to add an optional ticker parameter here?
    @classmethod
    def latest(cls, source: str, n: int = 1) -> pd.DataFrame:
        """Return the last N rows per symbol or table."""
        query = f"""
        SELECT * FROM {source}
        ORDER BY date DESC
        LIMIT {n}
        """
        df = cls.client.query(query)
        return cls._format_dataframe(df)

    @classmethod
    def describe(cls, source: str) -> pd.DataFrame:
        """Return column types, non-null counts, basic stats."""
        query = f"DESCRIBE TABLE {source}"
        df = cls.client.query(query)
        return df

    @classmethod
    def column_types(cls, source: str) -> Dict[str, str]:
        """Return data types for each column in a table."""
        query = f"SHOW COLUMNS FROM {source}"
        # will return a dataframe with 'field' and 'type' columns
        df = cls.client.query(query)
        return dict(zip(df["field"], df["type"]))

    # order here too?
    @classmethod
    def stream(cls, source: str, batch_size: int = 10000):
        """
        Yield data in chunks of batch_size.
        Example usage:
            for df_chunk in DataLoader.stream('equities', 5000):
                process(df_chunk)
        """
        offset = 0 # for pagination
        while True:
            query = f"SELECT * FROM {source} ORDER BY date LIMIT {batch_size} OFFSET {offset}"
            df = cls.client.query(query)
            if df.empty:
                break
            yield cls._format_dataframe(df)
            offset += batch_size

    @classmethod
    def iter_chunks(cls, source: str, chunk_size: int = 10000):
        """Alias for stream."""
        return cls.stream(source, batch_size=chunk_size)

    @classmethod
    def batch_query(cls, sources: List[str], filters: Optional[Dict[str, Any]] = None):
        """Query multiple tables or symbols in a single call."""
        combined_df = pd.DataFrame()
        for source in sources:
            query = cls._build_query(source, filters=filters)
            df = cls.client.query(query, params=filters)
            formatted_df = cls._format_dataframe(df)
            combined_df = pd.concat([combined_df, formatted_df], axis=1)
        return combined_df