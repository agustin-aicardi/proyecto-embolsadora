#!/usr/bin/env python3
"""Verify InfluxDB response from CI integration test."""
import sys
import csv
import io
import math
from pathlib import Path


RESULT_PATH = Path("/tmp/result.txt")


def parse_result_file() -> list[dict[str, str]]:
    if not RESULT_PATH.exists():
        raise FileNotFoundError(f"{RESULT_PATH} not found")

    raw = RESULT_PATH.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError("Empty result file")

    lines = [line for line in raw.splitlines() if line.strip()]

    # Remove trailing HTTP status code if present (e.g. 200, 204, 500)
    if lines and lines[-1].isdigit():
        lines = lines[:-1]

    # Remove Influx CSV annotation lines
    csv_lines = [line for line in lines if not line.startswith("#")]

    if not csv_lines:
        raise ValueError("Empty CSV data after filtering annotations/status")

    reader = csv.DictReader(io.StringIO("\n".join(csv_lines)))
    rows = list(reader)

    if not rows:
        raise ValueError("No CSV rows in response")

    return rows


def build_values(rows: list[dict[str, str]]) -> dict[str, float | str]:
    vals: dict[str, float | str] = {}

    for row in rows:
        key = row.get("_field") or row.get("tag") or row.get("name") or ""
        value = row.get("_value", "")

        if not key or value == "":
            continue

        try:
            vals[key] = float(value)
        except ValueError:
            vals[key] = value

    return vals


def main() -> int:
    try:
        rows = parse_result_file()
        vals = build_values(rows)

        print(f"Values found: {vals}")

        errors: list[str] = []

        if "pack_count" not in vals:
            errors.append("pack_count not found")
        elif vals["pack_count"] != 123.0:
            errors.append(f"pack_count={vals['pack_count']}, expected 123")

        if "filled_weight" not in vals:
            errors.append("filled_weight not found")
        elif not isinstance(vals["filled_weight"], (int, float)) or not math.isclose(
            float(vals["filled_weight"]), 123.456, abs_tol=1e-3
        ):
            errors.append(f"filled_weight={vals['filled_weight']}, expected ~123.456")

        if errors:
            print("ERRORS:")
            for err in errors:
                print(f"  - {err}")
            return 3

        print("✓ All verification checks passed!")
        return 0

    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 4


if __name__ == "__main__":
    sys.exit(main())