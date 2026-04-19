#!/usr/bin/env python3
"""Verify InfluxDB response from CI integration test."""

import sys
import csv
import io
from pathlib import Path

RESULT_FILE = "/tmp/result.txt"


def load_csv():
    if not Path(RESULT_FILE).exists():
        print("ERROR: result.txt not found")
        sys.exit(1)

    raw = Path(RESULT_FILE).read_text().strip()

    if not raw:
        print("ERROR: result.txt empty")
        sys.exit(1)

    lines = [l for l in raw.splitlines() if l.strip()]

    # remove HTTP status code if present
    if lines[-1].isdigit():
        lines = lines[:-1]

    # remove influx annotation lines
    lines = [l for l in lines if not l.startswith("#")]

    if not lines:
        print("ERROR: no CSV data found")
        sys.exit(1)

    reader = csv.DictReader(io.StringIO("\n".join(lines)))
    return list(reader)


def extract_values(rows):
    vals = {}

    for r in rows:
        key = r.get("_field") or r.get("tag") or ""
        val = r.get("_value")

        if not key or val is None:
            continue

        try:
            vals[key] = float(val)
        except ValueError:
            vals[key] = val

    return vals


def main():
    rows = load_csv()

    if not rows:
        print("ERROR: no rows returned from Influx")
        sys.exit(2)

    vals = extract_values(rows)

    print("Values found:", vals)

    # minimal sanity check
    if len(vals) < 2:
        print("ERROR: too few values returned from Influx")
        sys.exit(3)

    print("✓ CI verification passed")
    sys.exit(0)


if __name__ == "__main__":
    main()