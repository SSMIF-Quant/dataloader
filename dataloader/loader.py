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
    def get_data(
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

        df["date"] = pd.to_datetime(df["date"])
        df = df.rename(columns={"date": "Date"})

        if "symbol" in df.columns:
            df = df.sort_values(["symbol", "Date"]).drop_duplicates(
                subset=["symbol", "Date"]
            )
        else:
            df = df.sort_values("Date").drop_duplicates(subset=["Date"])

        df.set_index("Date", inplace=True)

        if filters and source == "equities" and len(filters.get("symbol", [])) == 1:
            symbol = filters["symbol"][0]
            df = cls._rename_columns(symbol, df)

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

        symbols = filters.get("symbol", []) if filters else []
        select_expr = cls._resolve_columns(
            source, symbols, columns_list, column_pattern
        )

        query = f"SELECT {select_expr} FROM {source} WHERE 1=1"

        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    query += f" AND {key} IN %({key})s"
                else:
                    query += f" AND {key} = %({key})s"

        if limit:
            query += f" LIMIT {limit}"
        if offset:
            query += f" OFFSET {offset}"

        query += " ORDER BY date"

        return query

    @staticmethod
    def _resolve_columns(
        source: str,
        symbols: Optional[List[str]] = None,
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

        if source == "equities" and len(symbols or []) > 1:
            selected_cols.append("symbol")

        if columns_list:
            selected_cols.extend(columns_list)

        if column_pattern:
            for p in column_pattern:
                selected_cols.append(f"COLUMNS('{p}')")

        return ", ".join(selected_cols)

    @classmethod
    def show_tables(cls) -> List[str]:
        """
        Returns available tables.
        """
        query = f"SHOW TABLES FROM {cls.database}"
        df = cls.client.query(query)
        return df["name"].tolist()

    @classmethod
    def show_table_column(cls, source: str) -> List[str]:
        """
        Returns all columns for a given table.
        """
        query = f"SHOW COLUMNS FROM {cls.database}.{source}"
        df = cls.client.query(query)
        return df["field"].tolist()
