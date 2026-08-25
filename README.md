# Beyond Big-O

**A Cross-Language Empirical Study of Runtime, Memory and Cache Performance of Common Data Structures**

This repository is a reproducible starter framework for third-year Computer Engineering students. It compares equivalent data-structure workloads in Python, Java and C++ using identical generated datasets.

## Research question

How strongly do language runtime, data-structure implementation and workload characteristics affect observed runtime, memory use and cache behaviour beyond asymptotic complexity?

## Initial structures and operations

| Abstract structure | Python | Java | C++ | Operations |
|---|---|---|---|---|
| Dynamic array | `list` | `ArrayList` | `std::vector` | build, search, delete, traverse |
| Linked structure | custom singly linked list | `LinkedList` | `std::list` | build, search, delete, traverse |
| Hash table | `dict` | `HashMap` | `std::unordered_map` | build, search, delete, traverse |

The first study intentionally limits scope. Trees, queues, concurrency and alternative allocators should be added only after the base protocol is validated.

## Quick start

Requirements: Python 3.11+, Java 17+, a C++17 compiler and, for hardware counters, Linux `perf`.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
make datasets
make build
make smoke
make benchmark
make analyse
```

Generated outputs are written under `results/`. Raw measurements are never edited manually.

## Fairness rules

- All languages read the same dataset files.
- Dataset loading and CSV writing are excluded from measured operations.
- Each result includes hit counts and a post-deletion checksum.
- Java warm-up runs are required before recorded trials.
- Compiler, interpreter, JVM, operating system and hardware details must be recorded.
- Experiments must be repeated on an otherwise idle machine.
- Timing from different machines must never be pooled without modelling machine effects.

## Repository map

- `docs/RESEARCH_PROTOCOL.md` — formal methodology and validity controls
- `docs/GITHUB_SETUP.md` — beginner GitHub instructions
- `scripts/generate_datasets.py` — deterministic common datasets
- `src/` — language implementations
- `scripts/run_all.py` — build and execute the benchmark matrix
- `scripts/analyse_results.py` — validation, statistics and plots
- `tests/` — automated correctness checks
- `workbook/` — student research workbook

## Research integrity

This repository supports a research study; it does not guarantee journal acceptance. Students must understand the programs, keep an experiment log, report negative findings and preserve every raw measurement needed to reproduce the paper.

