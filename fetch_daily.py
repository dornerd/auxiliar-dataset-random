"""Fetch today's latest rates for USD, EUR, GBP into one CSV (one row per base/target pair)."""
from fetch_exchange_rates import fetch_rates, to_rows, write_csv

if __name__ == "__main__":
    rows = [row for base in ("USD", "EUR", "GBP") for row in to_rows(fetch_rates(base))]
    write_csv(rows, "daily_rates.csv")
    print(f"wrote {len(rows)} rows to daily_rates.csv")
