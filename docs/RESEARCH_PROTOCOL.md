# Research Protocol

## Working title

Beyond Big-O: A Cross-Language Empirical Study of Runtime, Memory and Cache Performance of Common Data Structures

## Research questions

- **RQ1:** How does language choice change the observed cost of equivalent data-structure operations?
- **RQ2:** At what input sizes do theoretical advantages become observable in practice?
- **RQ3:** How do access pattern and deletion rate affect runtime and cache behaviour?
- **RQ4:** Can a normalised suitability score recommend a structure for speed-, memory- or cache-constrained workloads?

## Hypotheses

- H1: Hash tables will provide lower search time than sequential structures for sufficiently large random workloads.
- H2: Linked structures will consume more memory per element and experience poorer cache locality than contiguous arrays.
- H3: Runtime effects will interact with language implementation, input size and operation mix.

## Independent variables

- Language: Python, Java, C++
- Structure: dynamic array, linked structure, hash table
- Input size: defined in `config/experiment.json`
- Workload: build, successful/unsuccessful search, deletion and traversal

## Dependent variables

- Operation time in nanoseconds
- Peak resident memory measured externally
- Cache references, cache misses and cache-miss rate on supported Linux systems
- Correctness indicators: query hits and checksum after deletion

## Controlled variables

- One physical machine for the primary experiment
- Same dataset files and random seed
- Fixed software versions and compiler flags
- Fixed power mode; no unrelated foreground tasks
- Dataset parsing and result writing outside timed regions
- Required warm-ups before recorded trials

## Dataset format

Each UTF-8 dataset has three lines:

1. Space-separated unique values
2. Space-separated search queries containing both present and absent values
3. Space-separated keys selected for deletion

The generator writes a SHA-256 manifest. Every benchmark record must be traceable to that manifest.

## Execution protocol

1. Record system metadata.
2. Generate datasets once and preserve their manifest.
3. Build C++ with `-O2 -std=c++17`; record the compiler version.
4. Compile Java and record the JVM version.
5. Run at least three unrecorded warm-ups per language/structure/size.
6. Randomise the recorded execution order.
7. Run at least ten recorded repetitions.
8. Stop if hit counts or checksums disagree; correctness precedes performance.
9. Preserve raw CSV files and analysis code.

## Statistical analysis

- Report median, mean, standard deviation and 95% confidence interval.
- Plot distributions, not only averages.
- Use non-parametric comparisons when normality is not credible.
- Report effect sizes and adjusted p-values for multiple comparisons.
- Treat language, structure, size and operation as separate factors.
- Never interpret statistical significance as practical importance by itself.

## Proposed Data Structure Suitability Score

For a candidate structure `s`:

`DSSS(s) = w_t*T_norm(s) + w_m*M_norm(s) + w_c*C_norm(s)`

Lower is better. The weights represent the application priorities and must sum to one. The paper must include sensitivity analysis across multiple weight combinations instead of presenting a single arbitrary ranking.

## Threats to validity

- Language libraries are idiomatic but not internally identical.
- Garbage collection and JIT compilation can affect Java measurements.
- Python allocation tracking is not directly comparable with native allocation.
- Hardware counters may be unavailable or restricted.
- A single machine limits external validity.
- Microbenchmarks do not represent complete applications.

These limitations must be reported, not hidden.

