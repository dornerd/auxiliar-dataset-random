"""Backfill GBP exchange rates YTD (2026-01-01 to today) into one CSV."""
from datetime import date

from fetch_exchange_rates import backfill_range, write_csv

if __name__ == "__main__":
    rows = backfill_range("GBP", date(2026, 1, 1), date.today())
    write_csv(rows, "gbp_ytd.csv")
    print(f"wrote {len(rows)} rows to gbp_ytd.csv")
