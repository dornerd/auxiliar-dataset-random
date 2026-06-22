"""Fetch exchange rates (latest or historical) from exchangerate-api.com and flatten for table storage."""
import csv
import json
import os
import sys
import urllib.request
from datetime import date, datetime, timedelta, timezone


def _call(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.load(resp)
    if data.get("result") != "success":
        raise RuntimeError(f"exchangerate-api error: {data.get('error-type')}")
    return data


def fetch_rates(base: str = "USD") -> dict:
    api_key = os.environ["EXCHANGERATE_API_KEY"]  # ponytail: never hardcode the key, export it before running
    return _call(f"https://v6.exchangerate-api.com/v6/{api_key}/latest/{base}")


def fetch_history(base: str, day: date) -> dict:
    """Historical data goes back to 1990 (older dates carry fewer/legacy currencies, e.g. DEM before EUR existed)."""
    api_key = os.environ["EXCHANGERATE_API_KEY"]
    url = f"https://v6.exchangerate-api.com/v6/{api_key}/history/{base}/{day.year}/{day.month}/{day.day}"
    return _call(url)


def to_rows(data: dict) -> list[dict]:
    """One row per (base, target) pair -- the shape a Databricks table wants."""
    fetched_at = datetime.now(timezone.utc).isoformat()
    if "year" in data:
        rate_date = f"{data['year']:04d}-{data['month']:02d}-{data['day']:02d}"
    else:
        rate_date = datetime.strptime(
            data["time_last_update_utc"], "%a, %d %b %Y %H:%M:%S %z"
        ).date().isoformat()
    return [
        {
            "base_code": data["base_code"],
            "target_code": target,
            "rate": rate,
            "rate_date": rate_date,
            "fetched_at": fetched_at,
        }
        for target, rate in data["conversion_rates"].items()
    ]


def backfill_range(base: str, start: date, end: date) -> list[dict]:
    """One history call per day in [start, end] -- a YTD backfill from Jan 1 means ~170 requests."""
    rows = []
    day = start
    while day <= end:
        rows.extend(to_rows(fetch_history(base, day)))
        day += timedelta(days=1)
    return rows


def backfill(base: str, days: int) -> list[dict]:
    today = datetime.now(timezone.utc).date()
    return backfill_range(base, today - timedelta(days=days), today - timedelta(days=1))


def write_csv(rows: list[dict], path: str) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)


def demo():
    sample = {
        "result": "success",
        "base_code": "USD",
        "time_last_update_utc": "Mon, 01 Jan 2024 00:00:01 +0000",
        "conversion_rates": {"USD": 1, "EUR": 0.9},
    }
    rows = to_rows(sample)
    assert len(rows) == 2
    assert rows[0]["base_code"] == "USD" and rows[1]["target_code"] == "EUR"

    hist_sample = {"result": "success", "base_code": "USD", "year": 1990, "month": 1, "day": 1,
                    "conversion_rates": {"DEM": 1.7}}
    hist_rows = to_rows(hist_sample)
    assert hist_rows[0]["rate_date"] == "1990-01-01"
    print("demo ok")


if __name__ == "__main__":
    if "--demo" in sys.argv:
        demo()
        sys.exit(0)

    if "--backfill-days" in sys.argv:
        n = int(sys.argv[sys.argv.index("--backfill-days") + 1])
        rows = backfill("USD", n)
    elif "--date" in sys.argv:
        day = date.fromisoformat(sys.argv[sys.argv.index("--date") + 1])  # YYYY-MM-DD
        rows = to_rows(fetch_history("USD", day))
    else:
        rows = to_rows(fetch_rates("USD"))

    if "--csv" in sys.argv:
        out_path = sys.argv[sys.argv.index("--csv") + 1]
        write_csv(rows, out_path)
        print(f"wrote {len(rows)} rows to {out_path}")
    else:
        print(json.dumps(rows, indent=2))
