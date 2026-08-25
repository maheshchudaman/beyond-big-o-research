#!/usr/bin/env python3
"""Validate results and create dependency-free descriptive summaries."""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path


OPERATIONS = ["insert_ns", "search_ns", "delete_ns", "traverse_ns"]


def read_rows(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def validate(rows: list[dict[str, str]]) -> None:
    if not rows:
        raise ValueError("Input contains no result rows")
    required = {"language", "structure", "dataset", "n", "repeat", "hits", "checksum", *OPERATIONS}
    missing = required.difference(rows[0])
    if missing:
        raise ValueError(f"Missing columns: {sorted(missing)}")
    correctness: dict[tuple[str, int], set[tuple[int, int]]] = defaultdict(set)
    for row in rows:
        for operation in OPERATIONS:
            if int(row[operation]) < 0:
                raise ValueError("Negative timing detected")
        correctness[(row["dataset"], int(row["n"]))].add((int(row["hits"]), int(row["checksum"])))
    failures = [key for key, outcomes in correctness.items() if len(outcomes) != 1]
    if failures:
        raise ValueError(f"Correctness failure for datasets: {failures}")


def write_tidy(rows: list[dict[str, str]], path: Path) -> dict[tuple[str, str, int, str], list[int]]:
    groups: dict[tuple[str, str, int, str], list[int]] = defaultdict(list)
    fields = ["language", "structure", "dataset", "n", "repeat", "operation", "time_ns", "hits", "checksum"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            for operation_field in OPERATIONS:
                operation = operation_field.removesuffix("_ns")
                value = int(row[operation_field])
                key = (row["language"], row["structure"], int(row["n"]), operation)
                groups[key].append(value)
                writer.writerow({
                    "language": row["language"], "structure": row["structure"], "dataset": row["dataset"],
                    "n": row["n"], "repeat": row["repeat"], "operation": operation,
                    "time_ns": value, "hits": row["hits"], "checksum": row["checksum"],
                })
    return groups


def write_summary(groups: dict[tuple[str, str, int, str], list[int]], path: Path) -> None:
    fields = ["language", "structure", "n", "operation", "count", "mean_ns", "median_ns", "std_ns", "ci95_half_width_ns"]
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for key in sorted(groups):
            values = groups[key]
            std = statistics.stdev(values) if len(values) > 1 else 0.0
            writer.writerow(dict(zip(("language", "structure", "n", "operation"), key)) | {
                "count": len(values), "mean_ns": statistics.mean(values), "median_ns": statistics.median(values),
                "std_ns": std, "ci95_half_width_ns": 1.96 * std / math.sqrt(len(values)),
            })


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="results/raw/combined.csv")
    parser.add_argument("--output-dir", default="results/processed")
    args = parser.parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = read_rows(Path(args.input))
    validate(rows)
    groups = write_tidy(rows, output_dir / "tidy_results.csv")
    write_summary(groups, output_dir / "summary_statistics.csv")
    print(f"Validation passed for {len(rows)} rows. Outputs written to {output_dir}")


if __name__ == "__main__":
    main()
