# Data Validation Report

- Generated (UTC): 2026-05-07T12:00:48.592904+00:00
- Files checked: 4

## MES_c_0_ohlcv-1m_2021-01-01T00-00-00_2026-01-01T00-00-00.parquet [FAIL]
- Symbol: MES.c.0
- Rows: 1755853
- Range: 2021-01-03T23:00:00+00:00 -> 2025-12-31T21:59:00+00:00
- Duplicate timestamps: 0
- Out-of-order timestamps: 0
- Missing bars in small gaps: 65132
- Large gap segments (>120 min): 301
- Maximum gap (minutes): 4381
- Errors:
  - Missing required columns: ['contract']
  - Missing bars in small gaps 65132 > 0 (ignores gaps larger than 120 minutes)

## MGC_c_0_ohlcv-1m_2021-01-01T00-00-00_2026-01-01T00-00-00.parquet [FAIL]
- Symbol: MGC.c.0
- Rows: 832766
- Range: 2021-01-03T23:00:00+00:00 -> 2025-12-31T21:59:00+00:00
- Duplicate timestamps: 0
- Out-of-order timestamps: 0
- Missing bars in small gaps: 238544
- Large gap segments (>120 min): 1452
- Maximum gap (minutes): 23857
- Errors:
  - Missing required columns: ['contract']
  - Missing bars in small gaps 238544 > 0 (ignores gaps larger than 120 minutes)

## MNQ_c_0_ohlcv-1m_2021-01-01T00-00-00_2026-01-01T00-00-00.parquet [FAIL]
- Symbol: MNQ.c.0
- Rows: 1758746
- Range: 2021-01-03T23:00:00+00:00 -> 2025-12-31T21:59:00+00:00
- Duplicate timestamps: 0
- Out-of-order timestamps: 0
- Missing bars in small gaps: 62239
- Large gap segments (>120 min): 301
- Maximum gap (minutes): 4381
- Errors:
  - Missing required columns: ['contract']
  - Missing bars in small gaps 62239 > 0 (ignores gaps larger than 120 minutes)

## MYM_c_0_ohlcv-1m_2021-01-01T00-00-00_2026-01-01T00-00-00.parquet [FAIL]
- Symbol: MYM.c.0
- Rows: 1699952
- Range: 2021-01-03T23:00:00+00:00 -> 2025-12-31T21:59:00+00:00
- Duplicate timestamps: 0
- Out-of-order timestamps: 0
- Missing bars in small gaps: 121031
- Large gap segments (>120 min): 301
- Maximum gap (minutes): 4381
- Errors:
  - Missing required columns: ['contract']
  - Missing bars in small gaps 121031 > 0 (ignores gaps larger than 120 minutes)
