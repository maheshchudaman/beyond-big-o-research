#!/usr/bin/env python3
"""Generate deterministic, language-neutral benchmark datasets."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path


def write_dataset(path: Path, n: int, seed: int, query_fraction: float, delete_fraction: float) -> dict:
    rng = random.Random(seed + n)
    values = list(range(n))
    rng.shuffle(values)

    query_count = max(10, int(n * query_fraction))
    present_count = query_count // 2
    queries = rng.sample(values, present_count)
    queries.extend(n + i for i in range(query_count - present_count))
    rng.shuffle(queries)

    delete_count = max(1, int(n * delete_fraction))
    deletes = rng.sample(values, delete_count)

    content = "\n".join(
        (
            " ".join(map(str, values)),
            " ".join(map(str, queries)),
            " ".join(map(str, deletes)),
        )
    ) + "\n"
    path.write_text(content, encoding="utf-8")
    return {
        "file": path.name,
        "n": n,
        "queries": len(queries),
        "deletes": len(deletes),
        "sha256": hashlib.sha256(content.encode()).hexdigest(),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/experiment.json")
    parser.add_argument("--output-dir", default="data/generated")
    args = parser.parse_args()

    config = json.loads(Path(args.config).read_text(encoding="utf-8"))
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    for n in config["sizes"]:
        manifest.append(
            write_dataset(
                output_dir / f"dataset_{n}.txt",
                n,
                config["seed"],
                config["query_fraction"],
                config["delete_fraction"],
            )
        )
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Generated {len(manifest)} datasets in {output_dir}")


if __name__ == "__main__":
    main()

