"""Client for fetching macro and equity data via FRED API and yfinance."""

import time
import warnings
from typing import ClassVar, Dict, List

import numpy as np
import pandas as pd
import requests
import yfinance as yf
from attrs import define

from ._exception import MacroDataFetchError, EquityDataFetchError

warnings.filterwarnings("ignore")  # Ignore yfinance warnings


@define
class FredYfClient:
    """Client for fetching macro data from FRED and equity data from yfinance."""

    _fred_key: str
    _fred_base: ClassVar[str] = "https://api.stlouisfed.org/fred/series/observations"

    def fred_fn(self, series_id: str, start: str, end: str) -> pd.Series:
        """Fetch a single FRED series and return it as a dated pd.Series."""
        params = {
            "api_key": self._fred_key,
            "series_id": series_id,
            "file_type": "json",
            "observation_start": start,
            "observation_end": end,
        }

        try:
            req = requests.get(type(self)._fred_base, params=params, timeout=15)
            req.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise MacroDataFetchError(f"HTTP error for FRED series {series_id}") from e

        observations = req.json().get("observations", [])
        if not observations:
            raise MacroDataFetchError(f"No observations for FRED series {series_id}")

        idx = [pd.to_datetime(obs["date"]) for obs in observations]
        vals = [
            float(obs["value"]) if obs["value"] != "." else np.nan
            for obs in observations
        ]

        return pd.Series(vals, index=idx, name=series_id)

    def fetch_macro_data(
        self, macro_tickers: List[str], start: str, end: str
    ) -> pd.DataFrame:
        """Fetch multiple FRED series and return a combined DataFrame."""
        raw_macro: Dict[str, pd.Series] = {}

        for ticker in macro_tickers:
            try:
                raw_macro[ticker] = self.fred_fn(ticker, start, end)
            except Exception as e:
                raise MacroDataFetchError(
                    f"Failed to fetch macro data for ticker {ticker}"
                ) from e

            time.sleep(0.25)

        return pd.DataFrame(raw_macro).sort_index().dropna(how="all")

    def fetch_equity_data(
        self, equity_tickers: List[str], start: str, end: str, adj_close: bool = True
    ) -> pd.DataFrame:
        """Download OHLCV data for equity tickers via yfinance."""
        try:
            data = yf.download(
                equity_tickers,
                start=start,
                end=end,
                auto_adjust=adj_close,
                progress=False,
            )
            return data
        except Exception as e:
            raise EquityDataFetchError(
                f"Failed to fetch equity data for tickers: {equity_tickers}"
            ) from e
