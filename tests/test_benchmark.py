from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src/python"))
import benchmark


class BenchmarkTests(unittest.TestCase):
    def test_all_structures_agree(self):
        values = list(range(50))
        queries = [0, 10, 49, 50, 70]
        deletes = [3, 10, 40]
        results = [benchmark.run_once(name, values, queries, deletes) for name in ("array", "linked", "hash")]
        self.assertEqual({result["hits"] for result in results}, {3})
        self.assertEqual(len({result["checksum"] for result in results}), 1)
        self.assertEqual(results[0]["checksum"], sum(values) - sum(deletes))


    def test_linked_list_removes_head_middle_and_missing(self):
        linked = benchmark.SinglyLinkedList([1, 2, 3])
        self.assertTrue(linked.remove(1))
        self.assertTrue(linked.remove(3))
        self.assertFalse(linked.remove(99))
        self.assertEqual(linked.checksum(), 2)


if __name__ == "__main__":
    unittest.main()
