#!/usr/bin/env python3
"""Build and run the complete cross-language benchmark matrix."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import random
import shutil
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
RAW = ROOT / "results" / "raw"


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.run(command, cwd=ROOT, check=True)


def build() -> dict[str, list[str]]:
    BUILD.mkdir(exist_ok=True)
    commands: dict[str, list[str]] = {
        "python": [sys.executable, str(ROOT / "src/python/benchmark.py")],
    }
    compiler = shutil.which("c++") or shutil.which("g++") or shutil.which("clang++")
    if compiler:
        run([compiler, "-O2", "-std=c++17", str(ROOT / "src/cpp/benchmark.cpp"), "-o", str(BUILD / "benchmark_cpp")])
        commands["cpp"] = [str(BUILD / "benchmark_cpp")]
    else:
        print("Warning: C++ compiler not found; C++ runs skipped")

    if shutil.which("javac") and shutil.which("java"):
        try:
            run(["javac", "-d", str(BUILD), str(ROOT / "src/java/Benchmark.java")])
            commands["java"] = ["java", "-cp", str(BUILD), "Benchmark"]
        except subprocess.CalledProcessError:
            print("Warning: Java launcher exists but no working JDK was found; Java runs skipped")
    else:
        print("Warning: Java 17+ not found; Java runs skipped")
    return commands


def combine_csv(files: list[Path], destination: Path) -> None:
    rows: list[dict[str, str]] = []
    fields: list[str] | None = None
    for path in files:
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            fields = reader.fieldnames
            rows.extend(reader)
    if fields is None:
        raise RuntimeError("No benchmark results were produced")
    with destination.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(ROOT / "config/experiment.json"))
    parser.add_argument("--smoke", action="store_true", help="Run one small dataset with one recorded repetition")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8"))

    if not (ROOT / "data/generated/manifest.json").exists():
        run([sys.executable, str(ROOT / "scripts/generate_datasets.py")])

    commands = build()
    RAW.mkdir(parents=True, exist_ok=True)
    datasets = sorted((ROOT / "data/generated").glob("dataset_*.txt"), key=lambda p: int(p.stem.split("_")[-1]))
    if args.smoke:
        datasets = datasets[:1]

    jobs = [(language, structure, dataset) for language in commands for structure in config["structures"] for dataset in datasets]
    random.Random(config["seed"]).shuffle(jobs)
    produced: list[Path] = []
    for language, structure, dataset in jobs:
        output = RAW / f"{language}_{structure}_{dataset.stem}.csv"
        command = commands[language] + [
            "--dataset", str(dataset),
            "--structure", structure,
            "--warmups", str(1 if args.smoke else config["warmups"]),
            "--repeats", str(1 if args.smoke else config["repeats"]),
            "--output", str(output),
        ]
        run(command)
        produced.append(output)

    combined = RAW / ("smoke_combined.csv" if args.smoke else "combined.csv")
    combine_csv(produced, combined)
    metadata = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version,
        "languages_completed": sorted(commands),
        "config": config,
    }
    (RAW / "environment.json").write_text(json.dumps(metadata, indent=2) + "\n", encoding="utf-8")
    print(f"Combined results: {combined}")


if __name__ == "__main__":
    main()
