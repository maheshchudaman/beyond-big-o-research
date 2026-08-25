#!/usr/bin/env python3
"""Python implementation of the common data-structure workload."""

from __future__ import annotations

import argparse
import csv
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass
class Node:
    value: int
    next: "Node | None" = None


class SinglyLinkedList:
    def __init__(self, values: Iterable[int] = ()) -> None:
        self.head: Node | None = None
        tail: Node | None = None
        for value in values:
            node = Node(value)
            if self.head is None:
                self.head = node
            else:
                assert tail is not None
                tail.next = node
            tail = node

    def contains(self, target: int) -> bool:
        current = self.head
        while current is not None:
            if current.value == target:
                return True
            current = current.next
        return False

    def remove(self, target: int) -> bool:
        previous: Node | None = None
        current = self.head
        while current is not None:
            if current.value == target:
                if previous is None:
                    self.head = current.next
                else:
                    previous.next = current.next
                return True
            previous, current = current, current.next
        return False

    def checksum(self) -> int:
        total = 0
        current = self.head
        while current is not None:
            total += current.value
            current = current.next
        return total


def load_dataset(path: Path) -> tuple[list[int], list[int], list[int]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if len(lines) != 3:
        raise ValueError(f"{path} must contain exactly three lines")
    return tuple([int(token) for token in line.split()] for line in lines)  # type: ignore[return-value]


def timed(function):
    start = time.perf_counter_ns()
    value = function()
    return time.perf_counter_ns() - start, value


def run_once(structure: str, values: list[int], queries: list[int], deletes: list[int]) -> dict:
    if structure == "array":
        insert_ns, container = timed(lambda: list(values))
        search_ns, hits = timed(lambda: sum(query in container for query in queries))

        def delete_array() -> None:
            for key in deletes:
                try:
                    container.remove(key)
                except ValueError:
                    pass

        delete_ns, _ = timed(delete_array)
        traverse_ns, checksum = timed(lambda: sum(container))
    elif structure == "linked":
        insert_ns, container = timed(lambda: SinglyLinkedList(values))
        search_ns, hits = timed(lambda: sum(container.contains(query) for query in queries))

        def delete_linked() -> None:
            for key in deletes:
                container.remove(key)

        delete_ns, _ = timed(delete_linked)
        traverse_ns, checksum = timed(container.checksum)
    elif structure == "hash":
        insert_ns, container = timed(lambda: {value: value for value in values})
        search_ns, hits = timed(lambda: sum(query in container for query in queries))

        def delete_hash() -> None:
            for key in deletes:
                container.pop(key, None)

        delete_ns, _ = timed(delete_hash)
        traverse_ns, checksum = timed(lambda: sum(container.keys()))
    else:
        raise ValueError(f"Unknown structure: {structure}")

    return {
        "insert_ns": insert_ns,
        "search_ns": search_ns,
        "delete_ns": delete_ns,
        "traverse_ns": traverse_ns,
        "hits": hits,
        "checksum": checksum,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--structure", choices=("array", "linked", "hash"), required=True)
    parser.add_argument("--warmups", type=int, default=3)
    parser.add_argument("--repeats", type=int, default=10)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    dataset_path = Path(args.dataset)
    values, queries, deletes = load_dataset(dataset_path)
    for _ in range(args.warmups):
        run_once(args.structure, values, queries, deletes)

    fields = ["language", "structure", "dataset", "n", "repeat", "insert_ns", "search_ns", "delete_ns", "traverse_ns", "hits", "checksum"]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for repeat in range(args.repeats):
            row = run_once(args.structure, values, queries, deletes)
            writer.writerow({"language": "python", "structure": args.structure, "dataset": dataset_path.name, "n": len(values), "repeat": repeat, **row})


if __name__ == "__main__":
    main()
