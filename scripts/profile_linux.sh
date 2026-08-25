#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 OUTPUT_PREFIX COMMAND [ARGS...]" >&2
  exit 2
fi

output_prefix="$1"
shift

if ! command -v perf >/dev/null 2>&1; then
  echo "perf is required for cache-counter profiling on Linux" >&2
  exit 1
fi

/usr/bin/time -v -o "${output_prefix}_memory.txt" \
  perf stat -x, -e cache-references,cache-misses,cycles,instructions \
  -o "${output_prefix}_perf.csv" -- "$@"

