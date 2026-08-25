# Result Data Dictionary

| Field | Meaning |
|---|---|
| `language` | `python`, `java` or `cpp` |
| `structure` | `array`, `linked` or `hash` |
| `dataset` | Input dataset filename |
| `n` | Number of initial values |
| `repeat` | Recorded repetition number |
| `insert_ns` | Structure construction time |
| `search_ns` | Time for all search queries |
| `delete_ns` | Time for all deletion keys |
| `traverse_ns` | Time to compute the final checksum |
| `hits` | Number of queries found |
| `checksum` | Sum of values remaining after deletion |

External profiling files may additionally contain peak RSS, cache references and cache misses. These values are separate from operation timings because measurement tools and permissions differ by operating system.

