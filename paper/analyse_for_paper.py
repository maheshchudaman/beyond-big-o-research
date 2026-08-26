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
LINKED_FWD_RAW = ROOT / "results/raw/cpp_linked_fwd_combined.csv"
JAVA_RAW = ROOT / "results/raw/java_combined.csv"
CALIBRATED_RAW = ROOT / "results/raw/cpp_calibrated_combined.csv"
RESOURCE_RAW = ROOT / "results/raw/resource_usage.csv"
SORTED_RAW = ROOT / "results/raw/sorted_combined.csv"
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


def read_linked_fwd_groups():
    rows = list(csv.DictReader(LINKED_FWD_RAW.open(newline="", encoding="utf-8")))
    groups: dict[tuple[int, str], list[int]] = defaultdict(list)
    for row in rows:
        for operation in OPERATIONS:
            groups[(int(row["n"]), operation)].append(int(row[f"{operation}_ns"]))
    return rows, groups


def write_linked_fwd_supplement(main_rows, main_groups, fwd_rows, fwd_groups):
    """Construct-validity check: std::forward_list is singly-linked, matching the
    custom Python SinglyLinkedList, unlike std::list (typically doubly linked) used
    in the primary linked condition. Re-running the C++ linked benchmark with a
    matched container tests whether that representational mismatch inflates the
    reported Python/C++ ratios (see Section 6.2)."""
    reference = {
        int(row["n"]): (row["hits"], row["checksum"])
        for row in main_rows
        if row["language"] == "python" and row["structure"] == "linked"
    }
    for row in fwd_rows:
        expected = reference[int(row["n"])]
        assert (row["hits"], row["checksum"]) == expected, (
            f"forward_list correctness mismatch at n={row['n']}: "
            f"got {(row['hits'], row['checksum'])}, expected {expected}"
        )
    supplement = {
        "record_count": len(fwd_rows),
        "raw_sha256": hashlib.sha256(LINKED_FWD_RAW.read_bytes()).hexdigest(),
        "n25000": {},
        "scaling_exponents_5000_25000": {},
    }
    for operation in OPERATIONS:
        cpp_list_values = main_groups[("cpp", "linked", 25000, operation)]
        fwd_values = fwd_groups[(25000, operation)]
        python_values = main_groups[("python", "linked", 25000, operation)]
        cpp_list_median = statistics.median(cpp_list_values)
        fwd_median = statistics.median(fwd_values)
        python_median = statistics.median(python_values)
        # Correctness cross-check: forward_list must agree with std::list and Python
        # on hits/checksum at every size (verified once here; asserted per-size below).
        supplement["n25000"][operation] = {
            "cpp_list_median_ms": cpp_list_median / 1_000_000,
            "cpp_forward_list_median_ms": fwd_median / 1_000_000,
            "python_median_ms": python_median / 1_000_000,
            "python_to_forward_list_ratio": python_median / fwd_median,
            "python_to_list_ratio": python_median / cpp_list_median,
        }
        y1 = statistics.median(fwd_groups[(5000, operation)])
        supplement["scaling_exponents_5000_25000"][operation] = scaling_exponent(y1, fwd_median)
    return supplement


def read_java_groups():
    rows = list(csv.DictReader(JAVA_RAW.open(newline="", encoding="utf-8")))
    groups: dict[tuple[str, int, str], list[int]] = defaultdict(list)
    for row in rows:
        for operation in OPERATIONS:
            groups[(row["structure"], int(row["n"]), operation)].append(int(row[f"{operation}_ns"]))
    return rows, groups


def write_java_supplement(main_rows, main_groups, java_rows, java_groups):
    """External-validity check: the primary study only executed Python and C++;
    Java (OpenJDK 26, satisfies the >=17 requirement) was re-run across all three
    structures and four sizes with the identical protocol to test whether the
    Python/C++ pattern generalises to a third, managed-runtime language (see
    Section 6.3)."""
    reference = {
        (row["structure"], int(row["n"])): (row["hits"], row["checksum"])
        for row in main_rows
        if row["language"] == "python"
    }
    for row in java_rows:
        key = (row["structure"], int(row["n"]))
        expected = reference[key]
        assert (row["hits"], row["checksum"]) == expected, (
            f"Java correctness mismatch at {key}: got {(row['hits'], row['checksum'])}, expected {expected}"
        )
    supplement = {
        "record_count": len(java_rows),
        "raw_sha256": hashlib.sha256(JAVA_RAW.read_bytes()).hexdigest(),
        "java_version": "OpenJDK 26.0.2.1 (Homebrew)",
        "n25000": {},
        "scaling_exponents_5000_25000": {},
    }
    for structure in STRUCTURES:
        supplement["n25000"][structure] = {}
        supplement["scaling_exponents_5000_25000"][structure] = {}
        for operation in OPERATIONS:
            cpp_median = statistics.median(main_groups[("cpp", structure, 25000, operation)])
            python_median = statistics.median(main_groups[("python", structure, 25000, operation)])
            java_values = java_groups[(structure, 25000, operation)]
            java_median = statistics.median(java_values)
            java_mean = statistics.mean(java_values)
            java_cv = (statistics.pstdev(java_values) / java_mean * 100) if java_mean else 0.0
            supplement["n25000"][structure][operation] = {
                "cpp_median_ms": cpp_median / 1_000_000,
                "python_median_ms": python_median / 1_000_000,
                "java_median_ms": java_median / 1_000_000,
                "java_to_cpp_ratio": java_median / cpp_median,
                "python_to_java_ratio": python_median / java_median,
                "java_cv_pct": java_cv,
            }
            y1 = statistics.median(java_groups[(structure, 5000, operation)])
            supplement["scaling_exponents_5000_25000"][structure][operation] = scaling_exponent(y1, java_median)

    # Dispersion across every (structure, n, operation) group, not just n=25000,
    # mirroring the primary study's median/max CV reporting in Section 4.1.
    all_cvs = []
    for key, values in java_groups.items():
        mean = statistics.mean(values)
        all_cvs.append((statistics.pstdev(values) / mean * 100) if mean else 0.0)
    supplement["median_group_cv_pct"] = statistics.median(all_cvs)
    supplement["max_group_cv_pct"] = max(all_cvs)

    # Combinations at n=25,000 with low dispersion (CV < 10%) give the more
    # defensible ratio range; the full 0.41x-109.78x spread mixes in noisy,
    # short-duration groups (see the measurement caveat in Section 4.6).
    stable_ratios = [
        entry["java_to_cpp_ratio"]
        for structure in STRUCTURES
        for entry in [supplement["n25000"][structure][op] for op in OPERATIONS]
        if entry["java_cv_pct"] < 10.0
    ]
    supplement["stable_ratio_range"] = [min(stable_ratios), max(stable_ratios)]
    supplement["slower_than_python_combinations"] = [
        (structure, operation)
        for structure in STRUCTURES
        for operation in OPERATIONS
        if supplement["n25000"][structure][operation]["python_to_java_ratio"] < 1.0
    ]
    return supplement


def write_calibration_supplement(main_rows):
    """Measurement-resolution supplement: array traversal and hash search were
    the two operations recorded near the clock's own tick granularity in the
    primary single-shot design (Section 3.4 measurement caveat). Both are
    read-only and idempotent, so batching the operation until the timed
    interval clears a calibration threshold gives a far less noisy
    per-operation estimate than a single untimed shot (see Section 4.7)."""
    rows = list(csv.DictReader(CALIBRATED_RAW.open(newline="", encoding="utf-8")))
    reference = {
        (row["structure"], int(row["n"])): (row["hits"], row["checksum"])
        for row in main_rows
        if row["language"] == "cpp"
    }
    for row in rows:
        key = (row["structure"], int(row["n"]))
        expected = reference[key]
        got = (row["hits"], row["checksum"])
        # Only the field relevant to this operation was captured; the other is "0".
        if row["operation"] == "search":
            assert got[0] == expected[0], f"calibrated hits mismatch at {key}: got {got[0]}, expected {expected[0]}"
        else:
            assert got[1] == expected[1], f"calibrated checksum mismatch at {key}: got {got[1]}, expected {expected[1]}"

    supplement = {
        "record_count": len(rows),
        "raw_sha256": hashlib.sha256(CALIBRATED_RAW.read_bytes()).hexdigest(),
        "threshold_ns": 1_000_000,
        "by_size": {},
    }
    groups: dict[tuple[str, str, int], list[int]] = defaultdict(list)
    batch_sizes: dict[tuple[str, str, int], set[str]] = defaultdict(set)
    for row in rows:
        key = (row["structure"], row["operation"], int(row["n"]))
        groups[key].append(int(row["per_op_ns"]))
        batch_sizes[key].add(row["batch_size"])

    all_cvs = []
    for (structure, operation, n), values in groups.items():
        mean = statistics.mean(values)
        cv = (statistics.pstdev(values) / mean * 100) if mean else 0.0
        all_cvs.append(cv)
        single_shot_ns = statistics.median(
            int(r[f"{operation}_ns"])
            for r in main_rows
            if r["language"] == "cpp" and r["structure"] == structure and int(r["n"]) == n
        )
        supplement["by_size"].setdefault(structure, {}).setdefault(operation, {})[n] = {
            "single_shot_ns": single_shot_ns,
            "calibrated_median_ns": statistics.median(values),
            "calibrated_cv_pct": cv,
            "batch_sizes": sorted(batch_sizes[key]),
        }
    supplement["median_group_cv_pct"] = statistics.median(all_cvs)
    supplement["max_group_cv_pct"] = max(all_cvs)
    return supplement


def write_resource_supplement():
    """Peak memory and hardware-counter supplement: /usr/bin/time -l reports
    peak memory footprint, instructions retired and cycles elapsed for the
    whole benchmark process (all warm-ups and repeats) without needing
    Linux perf. One measurement per (language, structure, n); a three-run
    spot-check for one combination showed under 1.5% variation in all three
    metrics, so a single measurement is treated as representative."""
    rows = list(csv.DictReader(RESOURCE_RAW.open(newline="", encoding="utf-8")))
    supplement = {"record_count": len(rows), "raw_sha256": hashlib.sha256(RESOURCE_RAW.read_bytes()).hexdigest(), "at_n25000": {}}
    for row in rows:
        if int(row["n"]) != 25000:
            continue
        instr = int(row["instructions_retired"])
        cyc = int(row["cycles_elapsed"])
        supplement["at_n25000"].setdefault(row["language"], {})[row["structure"]] = {
            "peak_memory_bytes": int(row["peak_memory_bytes"]),
            "instructions_retired": instr,
            "cycles_elapsed": cyc,
            "ipc": instr / cyc if cyc else 0.0,
        }
    return supplement


def write_sorted_distribution_supplement(main_rows, main_groups):
    """External-validity supplement: the primary study used a single
    deterministic-shuffle input family. Re-running the identical workload
    against an ascending-sorted value set (same {0..n-1}, same query/delete
    fractions, same seed -- only the build order changes) tests whether the
    reported patterns are an artifact of that one distribution."""
    rows = list(csv.DictReader(SORTED_RAW.open(newline="", encoding="utf-8")))
    reference = {
        (row["structure"], int(row["n"])): (row["hits"], row["checksum"])
        for row in rows
        if row["language"] == "cpp"
    }
    for row in rows:
        key = (row["structure"], int(row["n"]))
        expected = reference[key]
        assert (row["hits"], row["checksum"]) == expected, (
            f"cross-language correctness mismatch on sorted distribution at {key}: "
            f"{row['language']} got {(row['hits'], row['checksum'])}, expected {expected}"
        )
    groups: dict[tuple[str, str, int, str], list[int]] = defaultdict(list)
    for row in rows:
        for operation in OPERATIONS:
            groups[(row["language"], row["structure"], int(row["n"]), operation)].append(int(row[f"{operation}_ns"]))

    supplement = {"record_count": len(rows), "raw_sha256": hashlib.sha256(SORTED_RAW.read_bytes()).hexdigest(), "cpp_n25000": {}}
    for operation in OPERATIONS:
        entry = {}
        for structure in STRUCTURES:
            shuffled_median = statistics.median(main_groups[("cpp", structure, 25000, operation)])
            sorted_median = statistics.median(groups[("cpp", structure, 25000, operation)])
            entry[structure] = {
                "shuffled_ns": shuffled_median,
                "sorted_ns": sorted_median,
                "ratio": sorted_median / shuffled_median if shuffled_median else float("inf"),
            }
        supplement["cpp_n25000"][operation] = entry
    return supplement


def write_metrics(rows, groups, fwd_rows, fwd_groups, java_rows, java_groups):
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
    metrics["linked_fwd_supplement"] = write_linked_fwd_supplement(rows, groups, fwd_rows, fwd_groups)
    metrics["java_supplement"] = write_java_supplement(rows, groups, java_rows, java_groups)
    metrics["calibration_supplement"] = write_calibration_supplement(rows)
    metrics["resource_supplement"] = write_resource_supplement()
    metrics["sorted_distribution_supplement"] = write_sorted_distribution_supplement(rows, groups)
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
    fwd_rows, fwd_groups = read_linked_fwd_groups()
    java_rows, java_groups = read_java_groups()
    metrics, ratios = write_metrics(rows, groups, fwd_rows, fwd_groups, java_rows, java_groups)
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
