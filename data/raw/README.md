# Raw data

This folder holds the data exactly as it was downloaded. Nothing here is
cleaned or changed.

## How to get it

```bash
python code/01_get_data.py
```

It takes about one minute and needs internet access. No account or key is
needed.

## What is here

- **`fred/`**: one CSV file per series from FRED (Federal Reserve Bank of
  St. Louis). There are 29 series: recession dates, interest rates, jobs,
  production, prices, credit, stocks, oil and the dollar. The list and the
  role of each series are in `code/01_get_data.py`.
- **`shiller/ie_data.xls`**: Robert Shiller's monthly US stock market data
  since 1871 (S&P 500 price, dividends, earnings, inflation, CAPE). We use it
  because FRED only has the last 10 years of the S&P 500.
- **`inventory.csv`**: one line per series, with how often it is published,
  how many values it has, how many are missing, and its first and last date.
- **`download_log.json`**: when the files were downloaded, and any failures.

## Why it is not on GitHub

Some series belong to other companies (Moody's, Cboe, NASDAQ, University of
Michigan). We may use them, but not share copies. So the files are not in the
repository: run the script to get them.

## Things to fix in the cleaning step

- Series come at different speeds: daily, weekly or monthly.
- October 2025 is missing for unemployment and prices (US government
  shutdown).
- Series start at different dates. The common period starts in 1967.
- The old dollar index stops in 2019. The new one starts in 2006.
- Shiller's file stops in September 2023 and has a messy layout.
- FRED gives today's corrected numbers, not the numbers known at the time.
