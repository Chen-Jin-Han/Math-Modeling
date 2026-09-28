#!/usr/bin/env python3
"""Stream a CSV file and emit a deterministic first-pass JSON profile."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


MISSING = {"", "na", "n/a", "nan", "null", "none", "-"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_file", type=Path)
    parser.add_argument("--delimiter", default=",")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    stats: dict[str, dict] = {}
    row_count = 0

    with args.csv_file.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle, delimiter=args.delimiter)
        if not reader.fieldnames:
            raise SystemExit("CSV has no header row")
        for name in reader.fieldnames:
            stats[name] = {
                "non_missing": 0,
                "missing": 0,
                "numeric": 0,
                "numeric_sum": 0.0,
                "min": None,
                "max": None,
                "unique_sample": set(),
                "unique_sample_truncated": False,
            }
        for row in reader:
            row_count += 1
            for name in reader.fieldnames:
                raw = (row.get(name) or "").strip()
                item = stats[name]
                if raw.lower() in MISSING:
                    item["missing"] += 1
                    continue
                item["non_missing"] += 1
                if len(item["unique_sample"]) < 10000:
                    item["unique_sample"].add(raw)
                else:
                    item["unique_sample_truncated"] = True
                try:
                    value = float(raw)
                except ValueError:
                    continue
                item["numeric"] += 1
                item["numeric_sum"] += value
                item["min"] = value if item["min"] is None else min(item["min"], value)
                item["max"] = value if item["max"] is None else max(item["max"], value)

    columns = {}
    for name, item in stats.items():
        numeric_count = item.pop("numeric")
        numeric_sum = item.pop("numeric_sum")
        unique_values = item.pop("unique_sample")
        item["unique_count_sample"] = len(unique_values)
        item["numeric_count"] = numeric_count
        item["numeric_mean"] = numeric_sum / numeric_count if numeric_count else None
        columns[name] = item

    resolved = args.csv_file.resolve()
    try:
        reported_path = resolved.relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        reported_path = args.csv_file.name
    report = {"file": reported_path, "rows": row_count, "columns": columns}
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    if args.output:
        args.output.write_text(rendered + "\n", encoding="utf-8")
    else:
        print(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
