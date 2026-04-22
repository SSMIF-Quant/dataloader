from attrs import define
from typing import ClassVar, List, Dict

import yfinance as yf
import requests
import warnings
import pandas as pd
import numpy as np
import time

from ._exception import MacroDataFetchError, EquityDataFetchError

warnings.filterwarnings("ignore")  # Ignore yfinance warnings


@define
class Fred_Yf_Client:
    """
    Client for fetching macro data from fred and equity data from yfinance.
    """

    _FRED_KEY: str
    _FRED_BASE: ClassVar[str] = "https://api.stlouisfed.org/fred/series/observations"

    def fred_fn(self, series_id: str, start: str, end: str) -> pd.Series:

        params = {
            "api_key": self._FRED_KEY,
            "series_id": series_id,
            "file_type": "json",
            "observation_start": start,
            "observation_end": end,
        }

        try:
            req = requests.get(type(self)._FRED_BASE, params=params, timeout=15)
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
