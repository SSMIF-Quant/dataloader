class MacroDataFetchError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)


class EquityDataFetchError(Exception):
    def __init__(self, msg: str):
        super().__init__(msg)
