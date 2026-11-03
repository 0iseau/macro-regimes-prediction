"""Stage 1 -- obtain the raw data.

Downloads, unchanged, every series the project uses to identify and predict
US macro regimes (recession vs expansion):

  - FRED series (St. Louis Fed), each at its native frequency (daily, weekly
    or monthly). They are grouped by role, top-down: first the regime labels
    and the published benchmark indicators, then the inputs of the
    econometric baselines, then the extra macro and cross-asset variables
    given to the machine-learning models.
  - Robert Shiller's monthly US stock market data (S&P 500 price, dividends,
    earnings, CAPE since 1871), because FRED only carries the last ten years
    of the S&P 500.

Nothing is cleaned, resampled or aligned here: that is stage 2. The script
ends with an inventory of what was downloaded and fails if a file is missing,
empty or unreadable.

Output (data/raw/):
  fred/<SERIES_ID>.csv     one file per FRED series, as published
  shiller/ie_data.xls      Shiller's spreadsheet, as published
  inventory.csv            per series: block, frequency, observations, dates
  download_log.json        when and from where each file was fetched

    python code/01_get_data.py
"""

from __future__ import annotations

import io
import json
import sys
import time
from datetime import datetime, timezone

import pandas as pd

from helpers import RAW, download

FRED_URL = "https://fred.stlouisfed.org/graph/fredgraph.csv?id={}"
SHILLER_URL = "http://www.econ.yale.edu/~shiller/data/ie_data.xls"

# Series id -> (block, description). The order of the blocks is the top-down
# order of the project: what defines the regimes, what the benchmarks use,
# then what only the machine-learning models get.
SERIES = {
    # 1. Regime labels and published benchmark indicators
    "USREC": ("label", "NBER recession indicator (1 = recession month)"),
    "RECPROUSM156N": ("benchmark", "Chauvet-Piger smoothed recession probability (%)"),
    "SAHMREALTIME": ("benchmark", "Sahm rule recession indicator, real time"),
    # 2. Yield curve: input of the Estrella-Mishkin probit
    "GS10": ("rates", "10-year Treasury constant maturity rate (%)"),
    "TB3MS": ("rates", "3-month Treasury bill, secondary market (%)"),
    "T10Y3M": ("rates", "10-year minus 3-month Treasury spread, daily (%)"),
    "GS2": ("rates", "2-year Treasury constant maturity rate (%)"),
    "FEDFUNDS": ("rates", "Effective federal funds rate (%)"),
    # 3. Coincident indicators: inputs of the Chauvet Markov-switching model
    "PAYEMS": ("activity", "Nonfarm payroll employment (thousands)"),
    "INDPRO": ("activity", "Industrial production index"),
    "W875RX1": ("activity", "Real personal income excluding transfers"),
    "CMRMTSPL": ("activity", "Real manufacturing and trade sales"),
    # 4. Labour market: input of the Sahm rule
    "UNRATE": ("labour", "Unemployment rate (%)"),
    "ICSA": ("labour", "Initial unemployment claims, weekly"),
    # 5. Further macro variables (machine-learning models only)
    "CPIAUCSL": ("inflation", "Consumer price index, all items"),
    "PCEPILFE": ("inflation", "Core PCE price index"),
    "M2SL": ("money", "M2 money stock"),
    "PERMIT": ("housing", "New private housing permits"),
    "HOUST": ("housing", "Housing starts"),
    "UMCSENT": ("sentiment", "University of Michigan consumer sentiment"),
    # 6. Cross-asset variables (machine-learning models only)
    "BAA": ("credit", "Moody's Baa corporate bond yield (%)"),
    "AAA": ("credit", "Moody's Aaa corporate bond yield (%)"),
    "BAA10YM": ("credit", "Baa yield minus 10-year Treasury (%)"),
    "NFCI": ("financial", "Chicago Fed national financial conditions index, weekly"),
    "VIXCLS": ("equity", "CBOE VIX, daily"),
    "NASDAQCOM": ("equity", "NASDAQ composite index, daily"),
    "WTISPLC": ("commodity", "WTI crude oil spot price"),
    "TWEXMMTH": ("fx", "Trade-weighted dollar, major currencies (ends 2019)"),
    "DTWEXBGS": ("fx", "Trade-weighted dollar, broad (starts 2006), daily"),
}

FRED_DIR = RAW / "fred"
SHILLER_DIR = RAW / "shiller"
PAUSE = 0.5  # seconds between requests


def frequency(dates: pd.Series) -> str:
    """Name the sampling frequency from the median gap between observations."""
    gap = dates.diff().dt.days.median()
    if gap <= 3:
        return "daily"
    if gap <= 8:
        return "weekly"
    if gap <= 35:
        return "monthly"
    return "quarterly or lower"


def get_fred(series_id: str) -> dict:
    content = download(FRED_URL.format(series_id))
    path = FRED_DIR / f"{series_id}.csv"
    path.write_bytes(content)

    df = pd.read_csv(io.BytesIO(content))
    if df.shape[1] != 2 or df.columns[1] != series_id:
        raise ValueError(f"{series_id}: unexpected columns {list(df.columns)}")
    dates = pd.to_datetime(df.iloc[:, 0])
    values = pd.to_numeric(df.iloc[:, 1], errors="coerce")
    return {
        "series": series_id,
        "block": SERIES[series_id][0],
        "description": SERIES[series_id][1],
        "frequency": frequency(dates),
        "observations": len(df),
        "missing": int(values.isna().sum()),
        "first": dates.min().date(),
        "last": dates.max().date(),
        "url": FRED_URL.format(series_id),
    }


def get_shiller() -> dict:
    content = download(SHILLER_URL)
    path = SHILLER_DIR / "ie_data.xls"
    path.write_bytes(content)
    # Read only to verify the file: the sheet has a multi-line header that
    # stage 2 parses properly.
    sheet = pd.read_excel(path, sheet_name="Data", header=None)
    dates = pd.to_numeric(sheet.iloc[:, 0], errors="coerce").dropna()
    return {
        "series": "SHILLER",
        "block": "equity",
        "description": "Shiller monthly S&P 500 price, dividends, earnings, CAPE",
        "frequency": "monthly",
        "observations": len(dates),
        "missing": None,
        "first": f"{dates.min():.2f}",
        "last": f"{dates.max():.2f}",
        "url": SHILLER_URL,
    }


def main() -> int:
    FRED_DIR.mkdir(parents=True, exist_ok=True)
    SHILLER_DIR.mkdir(parents=True, exist_ok=True)
    started = datetime.now(timezone.utc).isoformat(timespec="seconds")

    rows, failures = [], []
    print(f"Downloading {len(SERIES)} FRED series and Shiller's data to {RAW}", flush=True)
    for i, series_id in enumerate(SERIES, start=1):
        print(f"[{i:2d}/{len(SERIES)}] {series_id} ...", end=" ", flush=True)
        try:
            rows.append(get_fred(series_id))
            print("ok", flush=True)
        except Exception as exc:  # one bad series must not stop the others
            failures.append((series_id, str(exc)))
            print(f"FAIL: {exc}", flush=True)
        time.sleep(PAUSE)
    print("[--] Shiller ...", end=" ", flush=True)
    try:
        rows.append(get_shiller())
        print("ok", flush=True)
    except Exception as exc:
        failures.append(("SHILLER", str(exc)))
        print(f"FAIL: {exc}", flush=True)

    inventory = pd.DataFrame(rows)
    inventory.to_csv(RAW / "inventory.csv", index=False)
    (RAW / "download_log.json").write_text(json.dumps(
        {"started_utc": started,
         "finished_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
         "files": len(rows), "failures": failures},
        indent=2))

    print()
    print(inventory.drop(columns=["url", "description"]).to_string(index=False))
    if failures:
        print(f"\n{len(failures)} download(s) failed: {[f[0] for f in failures]}")
        return 1
    print(f"\nAll {len(rows)} files downloaded to {RAW}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
