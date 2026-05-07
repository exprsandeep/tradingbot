from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import yaml


@dataclass
class FileValidationResult:
    file: str
    symbol: str
    rows: int
    start_ts_utc: str
    end_ts_utc: str
    duplicate_timestamps: int
    out_of_order_timestamps: int
    missing_bars_small_gaps: int
    large_gap_segments: int
    max_gap_minutes: int
    missing_required_columns: list[str]
    alignment_3m_ok: bool
    alignment_15m_ok: bool
    alignment_1h_ok: bool
    passed: bool
    errors: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate downloaded futures parquet data")
    parser.add_argument(
        "--config",
        default="config/data_requirements.yaml",
        help="Path to YAML requirements config",
    )
    parser.add_argument(
        "--data-dir",
        default="data/raw",
        help="Directory containing parquet files",
    )
    parser.add_argument(
        "--glob",
        default="*.parquet",
        help="Glob pattern for parquet files",
    )
    return parser.parse_args()


def read_config(path: str) -> dict[str, Any]:
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def can_resample(df: pd.DataFrame, rule: str) -> bool:
    required_ohlcv = {"open", "high", "low", "close", "volume"}
    if df.empty or not required_ohlcv.issubset(df.columns):
        return False
    agg = {
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum",
    }
    resampled = df.sort_index().resample(rule).agg(agg).dropna()
    return len(resampled) > 0


def validate_file(
    path: Path,
    required_columns: list[str],
    thresholds: dict[str, Any],
    max_gap_for_missing_minutes: int = 120,
) -> FileValidationResult:
    df = pd.read_parquet(path)
    if df.empty:
        return FileValidationResult(
            file=path.name,
            symbol="unknown",
            rows=0,
            start_ts_utc="",
            end_ts_utc="",
            duplicate_timestamps=0,
            out_of_order_timestamps=0,
            missing_bars_small_gaps=0,
            large_gap_segments=0,
            max_gap_minutes=0,
            missing_required_columns=required_columns,
            alignment_3m_ok=False,
            alignment_15m_ok=False,
            alignment_1h_ok=False,
            passed=False,
            errors=["File is empty"],
        )

    missing_required_columns = [c for c in required_columns if c not in df.columns and c != "ts_utc"]

    ts = pd.DatetimeIndex(df.index)
    if ts.tz is None:
        ts = ts.tz_localize("UTC")
    else:
        ts = ts.tz_convert("UTC")

    duplicate_timestamps = int(ts.duplicated().sum())
    out_of_order_timestamps = int((ts.to_series().diff().dropna() < pd.Timedelta(0)).sum())

    ts_sorted = ts.sort_values().drop_duplicates()
    diffs = ts_sorted.to_series().diff().dropna()
    gap_minutes = (diffs / pd.Timedelta(minutes=1)).astype(int)

    small_gaps = gap_minutes[(gap_minutes > 1) & (gap_minutes <= max_gap_for_missing_minutes)]
    large_gaps = gap_minutes[gap_minutes > max_gap_for_missing_minutes]

    missing_bars_small_gaps = int((small_gaps - 1).sum()) if len(small_gaps) else 0
    large_gap_segments = int(len(large_gaps))
    max_gap_minutes = int(gap_minutes.max()) if len(gap_minutes) else 0

    symbol = str(df["symbol"].iloc[0]) if "symbol" in df.columns and len(df) else "unknown"

    df_for_resample = df.copy()
    df_for_resample.index = ts
    alignment_3m_ok = can_resample(df_for_resample, "3min")
    alignment_15m_ok = can_resample(df_for_resample, "15min")
    alignment_1h_ok = can_resample(df_for_resample, "1h")

    errors: list[str] = []

    max_dupes = int(thresholds.get("max_duplicate_timestamps", 0))
    max_out_of_order = int(thresholds.get("max_out_of_order_records", 0))
    max_missing = int(thresholds.get("max_missing_bars_during_active_session", 0))

    if missing_required_columns:
        errors.append(f"Missing required columns: {missing_required_columns}")
    if duplicate_timestamps > max_dupes:
        errors.append(f"Duplicate timestamps {duplicate_timestamps} > {max_dupes}")
    if out_of_order_timestamps > max_out_of_order:
        errors.append(f"Out-of-order timestamps {out_of_order_timestamps} > {max_out_of_order}")
    if missing_bars_small_gaps > max_missing:
        errors.append(
            f"Missing bars in small gaps {missing_bars_small_gaps} > {max_missing} "
            f"(ignores gaps larger than {max_gap_for_missing_minutes} minutes)"
        )

    passed = len(errors) == 0

    return FileValidationResult(
        file=path.name,
        symbol=symbol,
        rows=int(len(df)),
        start_ts_utc=ts_sorted.min().isoformat(),
        end_ts_utc=ts_sorted.max().isoformat(),
        duplicate_timestamps=duplicate_timestamps,
        out_of_order_timestamps=out_of_order_timestamps,
        missing_bars_small_gaps=missing_bars_small_gaps,
        large_gap_segments=large_gap_segments,
        max_gap_minutes=max_gap_minutes,
        missing_required_columns=missing_required_columns,
        alignment_3m_ok=alignment_3m_ok,
        alignment_15m_ok=alignment_15m_ok,
        alignment_1h_ok=alignment_1h_ok,
        passed=passed,
        errors=errors,
    )


def write_report(results: list[FileValidationResult], report_dir: Path) -> tuple[Path, Path]:
    report_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    json_path = report_dir / f"data_validation_{timestamp}.json"
    md_path = report_dir / f"data_validation_{timestamp}.md"

    payload = [asdict(r) for r in results]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    lines = [
        "# Data Validation Report",
        "",
        f"- Generated (UTC): {datetime.now(timezone.utc).isoformat()}",
        f"- Files checked: {len(results)}",
        "",
    ]

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        lines.extend(
            [
                f"## {r.file} [{status}]",
                f"- Symbol: {r.symbol}",
                f"- Rows: {r.rows}",
                f"- Range: {r.start_ts_utc} -> {r.end_ts_utc}",
                f"- Duplicate timestamps: {r.duplicate_timestamps}",
                f"- Out-of-order timestamps: {r.out_of_order_timestamps}",
                f"- Missing bars in small gaps: {r.missing_bars_small_gaps}",
                f"- Large gap segments (>120 min): {r.large_gap_segments}",
                f"- Maximum gap (minutes): {r.max_gap_minutes}",
            ]
        )
        if r.errors:
            lines.append("- Errors:")
            for e in r.errors:
                lines.append(f"  - {e}")
        lines.append("")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return json_path, md_path


def main() -> None:
    args = parse_args()
    cfg = read_config(args.config)

    thresholds = cfg.get("data_quality", {}).get("thresholds", {})
    required_columns = cfg.get("historical_data", {}).get("required_columns", [])
    report_dir = Path(cfg.get("outputs", {}).get("quality_reports_dir", "reports/data_quality"))

    files = sorted(Path(args.data_dir).glob(args.glob))
    if not files:
        raise FileNotFoundError(f"No files found in {args.data_dir} matching {args.glob}")

    results = [validate_file(p, required_columns, thresholds) for p in files]
    json_path, md_path = write_report(results, report_dir)

    failed = [r for r in results if not r.passed]
    print(f"Checked {len(results)} files. Failed: {len(failed)}")
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")

    if failed and cfg.get("data_quality", {}).get("fail_on_quality_error", True):
        raise SystemExit(1)


if __name__ == "__main__":
    main()

