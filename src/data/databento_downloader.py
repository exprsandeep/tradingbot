from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import pandas as pd
import databento as db


@dataclass
class DataRequest:
    dataset: str
    symbol: str
    schema: str
    start: str
    end: str
    stype_in: str = "continuous"
    output_dir: str = "data/raw"


class DatabentoDownloader:
    """
    Download historical futures data for backtests and save as parquet.
    """

    def __init__(self, api_key: str):
        self.client = db.Historical(api_key)

    def fetch(self, request: DataRequest) -> Path:
        data = self.client.timeseries.get_range(
            dataset=request.dataset,
            symbols=[request.symbol],
            schema=request.schema,
            stype_in=request.stype_in,
            start=request.start,
            end=request.end,
        )

        df: pd.DataFrame = data.to_df()
        if df.empty:
            raise ValueError(
                f"No data returned for {request.symbol} in {request.start} -> {request.end}"
            )

        output_path = self._output_path(request)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.to_parquet(output_path, index=True)
        return output_path

    def _output_path(self, request: DataRequest) -> Path:
        safe_symbol = request.symbol.replace(".", "_")
        filename = (
            f"{safe_symbol}_{request.schema}_{request.start}_{request.end}.parquet"
            .replace(":", "-")
            .replace("/", "-")
        )
        return Path(request.output_dir) / filename

