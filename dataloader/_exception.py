"""Custom exceptions for dataloader fetch errors."""


class MacroDataFetchError(Exception):
    """Raised when a FRED macro data request fails."""

    def __init__(self, msg: str):
        super().__init__(msg)


class EquityDataFetchError(Exception):
    """Raised when a yfinance equity data request fails."""

    def __init__(self, msg: str):
        super().__init__(msg)
