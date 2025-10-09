"""Clickhouse data loader"""

from typing import Any, Dict, List, Optional

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

    database: str = "ssmif_quant"
    client: Client = Manager.get_connection()

    def get_data(
        self,
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
        query = self._build_query(
            source, columns_list, column_pattern, filters, limit, offset
        )

        params = {}
        if filters:
            for key, value in filters.items():
                if isinstance(value, list):
                    params[key] = tuple(value)
                else:
                    params[key] = value

        return self.client.query(query, params)

    def _build_query(
        self,
        source: str,
        columns_list: Optional[List[str]] = None,
        column_pattern: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:

        select_expr = self._resolve_columns(columns_list, column_pattern)
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

    def _resolve_columns(
        self,
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

        if columns_list:
            selected_cols.extend(columns_list)

        if column_pattern:
            for p in column_pattern:
                selected_cols.append(f"COLUMNS('{p}')")

        return ", ".join(selected_cols)

    def show_tables(self) -> List[str]:
        """
        Returns available tables.
        """
        query = f"SHOW TABLES FROM {self.database}"
        df = self.client.query(query)
        return df["name"].tolist()

    def show_table_column(self, source: str) -> List[str]:
        """
        Returns all columns for a given table.
        """
        query = f"SHOW COLUMNS FROM {self.database}.{source}"
        df = self.client.query(query)
        return df["field"].tolist()
