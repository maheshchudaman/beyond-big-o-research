#!/usr/bin/env python3
"""Derive paper tables and figures from the immutable Mac benchmark CSV."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "results/raw/combined.csv"
OUT = ROOT / "paper/generated"
OPERATIONS = ("insert", "search", "delete", "traverse")
STRUCTURES = ("array", "linked", "hash")
LANGUAGES = ("cpp", "python")
SIZES = (1000, 5000, 10000, 25000)
COLORS = {"array": "#CC4B37", "linked": "#2F6DAE", "hash": "#2B8A6E"}


def font(size: int, bold: bool = False):
    candidates = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/System/Library/Fonts/Supplemental/Helvetica.ttc",
    ]
    for candidate in candidates:
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def read_groups():
    rows = list(csv.DictReader(RAW.open(newline="", encoding="utf-8")))
    groups: dict[tuple[str, str, int, str], list[int]] = defaultdict(list)
    for row in rows:
        for operation in OPERATIONS:
            groups[(row["language"], row["structure"], int(row["n"]), operation)].append(int(row[f"{operation}_ns"]))
    return rows, groups


def bootstrap_median_ci(values: list[int], seed: int, samples: int = 5000):
    rng = random.Random(seed)
    n = len(values)
    medians = sorted(statistics.median(rng.choices(values, k=n)) for _ in range(samples))
    return medians[int(0.025 * samples)], medians[int(0.975 * samples)]


def cliffs_delta(left: list[int], right: list[int]) -> float:
    greater = sum(a > b for a in left for b in right)
    lower = sum(a < b for a in left for b in right)
    return (greater - lower) / (len(left) * len(right))


def scaling_exponent(y1: float, y2: float, n1=5000, n2=25000) -> float:
    return math.log(y2 / y1) / math.log(n2 / n1)


def write_metrics(rows, groups):
    metrics = {
        "record_count": len(rows),
        "raw_sha256": hashlib.sha256(RAW.read_bytes()).hexdigest(),
        "n25000": {},
        "scaling_exponents_5000_25000": {},
        "submicrosecond_groups": [],
    }
    table_rows = []
    ratios = []
    for structure in STRUCTURES:
        metrics["n25000"][structure] = {}
        metrics["scaling_exponents_5000_25000"][structure] = {}
        for operation in OPERATIONS:
            entry = {}
            for language in LANGUAGES:
                values = groups[(language, structure, 25000, operation)]
                median = statistics.median(values)
                seed_material = f"{language}:{structure}:{operation}".encode()
                seed = int.from_bytes(hashlib.sha256(seed_material).digest()[:4], "big")
                low, high = bootstrap_median_ci(values, seed=seed)
                entry[language] = {
                    "median_ns": median,
                    "median_ms": median / 1_000_000,
                    "bootstrap_median_ci95_ns": [low, high],
                    "mean_ns": statistics.mean(values),
                    "std_ns": statistics.stdev(values),
                }
                if median < 1000:
                    metrics["submicrosecond_groups"].append([language, structure, 25000, operation, median])
                y1 = statistics.median(groups[(language, structure, 5000, operation)])
                metrics["scaling_exponents_5000_25000"][structure].setdefault(operation, {})[language] = scaling_exponent(y1, median)
            ratio = entry["python"]["median_ns"] / entry["cpp"]["median_ns"]
            delta = cliffs_delta(groups[("python", structure, 25000, operation)], groups[("cpp", structure, 25000, operation)])
            entry["python_to_cpp_median_ratio"] = ratio
            entry["cliffs_delta_python_vs_cpp"] = delta
            metrics["n25000"][structure][operation] = entry
            ratios.append((structure, operation, ratio))
            table_rows.append({
                "structure": structure, "operation": operation,
                "cpp_median_ms": f"{entry['cpp']['median_ms']:.6f}",
                "python_median_ms": f"{entry['python']['median_ms']:.6f}",
                "python_cpp_ratio": f"{ratio:.2f}", "cliffs_delta": f"{delta:.2f}",
            })

    all_cvs = []
    for values in groups.values():
        mean = statistics.mean(values)
        all_cvs.append(statistics.stdev(values) / mean if mean else 0.0)
    metrics["median_group_cv"] = statistics.median(all_cvs)
    metrics["max_group_cv"] = max(all_cvs)
    metrics["language_ratio_range_n25000"] = [min(x[2] for x in ratios), max(x[2] for x in ratios)]
    (OUT / "paper_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")
    with (OUT / "n25000_medians.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=table_rows[0].keys())
        writer.writeheader()
        writer.writerows(table_rows)
    return metrics, ratios


def draw_search_scaling(groups):
    width, height = 1800, 920
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((70, 35), "Median search workload time across input sizes", font=font(38, True), fill="#142B44")
    draw.text((70, 82), "Logarithmic axes; each workload contains 1% of n queries (minimum 10)", font=font(22), fill="#566575")
    panels = [("cpp", "C++17"), ("python", "Python 3.13")]
    x_ticks = [1000, 5000, 10000, 25000]
    y_ticks_ns = [1, 100, 10_000, 1_000_000, 100_000_000]
    for panel_index, (language, label) in enumerate(panels):
        left = 105 + panel_index * 860
        top, panel_w, panel_h = 180, 730, 610
        right, bottom = left + panel_w, top + panel_h
        draw.rectangle((left, top, right, bottom), outline="#9AA8B5", width=2)
        draw.text((left, 125), label, font=font(28, True), fill="#142B44")
        for tick in y_ticks_ns:
            y = bottom - (math.log10(tick) / 8) * panel_h
            draw.line((left, y, right, y), fill="#E3E8ED", width=1)
            label_text = f"{tick / 1_000_000:g} ms"
            draw.text((left - 86, y - 10), label_text, font=font(15), fill="#5E6B78")
        min_x, max_x = math.log10(1000), math.log10(25000)
        for tick in x_ticks:
            x = left + (math.log10(tick) - min_x) / (max_x - min_x) * panel_w
            draw.line((x, top, x, bottom), fill="#EEF1F4", width=1)
            draw.text((x - 25, bottom + 14), f"{tick:,}", font=font(16), fill="#5E6B78")
        for structure in STRUCTURES:
            points = []
            for n in SIZES:
                value = statistics.median(groups[(language, structure, n, "search")])
                if value <= 0:
                    continue
                x = left + (math.log10(n) - min_x) / (max_x - min_x) * panel_w
                y = bottom - (math.log10(max(1, value)) / 8) * panel_h
                points.append((x, y))
            if len(points) > 1:
                draw.line(points, fill=COLORS[structure], width=5)
            for x, y in points:
                draw.ellipse((x - 7, y - 7, x + 7, y + 7), fill=COLORS[structure])
        draw.text((left + 255, bottom + 52), "Input size (n)", font=font(18), fill="#142B44")
    legend_x = 615
    for structure in STRUCTURES:
        draw.rectangle((legend_x, 850, legend_x + 24, 874), fill=COLORS[structure])
        draw.text((legend_x + 34, 848), structure.title(), font=font(18), fill="#142B44")
        legend_x += 205
    image.save(OUT / "figure_1_search_scaling.png", dpi=(200, 200))


def draw_language_ratios(ratios):
    width, height = 1600, 980
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.text((70, 35), "Python-to-C++ median runtime ratio at n = 25,000", font=font(36, True), fill="#142B44")
    draw.text((70, 82), "Values above 1 indicate a longer Python runtime for this implementation and workload", font=font(21), fill="#566575")
    left, right, top, bottom = 410, 1490, 155, 900
    ticks = [1, 2, 5, 10, 20, 50, 100]
    max_log = math.log10(100)
    for tick in ticks:
        x = left + math.log10(tick) / max_log * (right - left)
        draw.line((x, top, x, bottom), fill="#E3E8ED", width=2)
        draw.text((x - 12, bottom + 15), f"{tick}x", font=font(17), fill="#5E6B78")
    ordered = sorted(ratios, key=lambda item: (STRUCTURES.index(item[0]), OPERATIONS.index(item[1])))
    row_h = 58
    for index, (structure, operation, ratio) in enumerate(ordered):
        y = top + index * row_h + 8
        label = f"{structure.title()} - {operation.title()}"
        draw.text((70, y + 7), label, font=font(19), fill="#142B44")
        x_end = left + math.log10(max(1, ratio)) / max_log * (right - left)
        draw.rounded_rectangle((left, y, x_end, y + 34), radius=8, fill=COLORS[structure])
        draw.text((min(x_end + 12, right - 75), y + 5), f"{ratio:.2f}x", font=font(18, True), fill="#142B44")
    image.save(OUT / "figure_2_language_ratios.png", dpi=(200, 200))


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows, groups = read_groups()
    metrics, ratios = write_metrics(rows, groups)
    draw_search_scaling(groups)
    draw_language_ratios(ratios)
    print(json.dumps({
        "records": metrics["record_count"],
        "sha256": metrics["raw_sha256"],
        "ratio_range": metrics["language_ratio_range_n25000"],
        "median_group_cv": metrics["median_group_cv"],
    }, indent=2))


if __name__ == "__main__":
    main()
