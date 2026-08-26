#include <algorithm>
#include <chrono>
#include <forward_list>
#include <fstream>
#include <iostream>
#include <list>
#include <numeric>
#include <sstream>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <vector>

using Clock = std::chrono::steady_clock;
using i64 = long long;

struct Dataset { std::vector<int> values, queries, deletes; };
struct Result { i64 insert_ns, search_ns, delete_ns, traverse_ns, hits, checksum; };

std::vector<int> parse_line(const std::string& line) {
    std::istringstream stream(line);
    std::vector<int> values;
    int value;
    while (stream >> value) values.push_back(value);
    return values;
}

Dataset load_dataset(const std::string& path) {
    std::ifstream input(path);
    if (!input) throw std::runtime_error("Cannot open dataset: " + path);
    std::string a, b, c;
    if (!std::getline(input, a) || !std::getline(input, b) || !std::getline(input, c))
        throw std::runtime_error("Dataset must contain three lines");
    return {parse_line(a), parse_line(b), parse_line(c)};
}

template <typename Function>
i64 elapsed(Function function) {
    auto start = Clock::now();
    function();
    return std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - start).count();
}

Result run_array(const Dataset& data) {
    std::vector<int> container;
    i64 hits = 0, checksum = 0;
    auto insert = elapsed([&] { container = data.values; });
    auto search = elapsed([&] {
        for (int q : data.queries) hits += std::find(container.begin(), container.end(), q) != container.end();
    });
    auto remove = elapsed([&] {
        for (int key : data.deletes) {
            auto it = std::find(container.begin(), container.end(), key);
            if (it != container.end()) container.erase(it);
        }
    });
    auto traverse = elapsed([&] { checksum = std::accumulate(container.begin(), container.end(), 0LL); });
    return {insert, search, remove, traverse, hits, checksum};
}

Result run_linked(const Dataset& data) {
    std::list<int> container;
    i64 hits = 0, checksum = 0;
    auto insert = elapsed([&] { container.assign(data.values.begin(), data.values.end()); });
    auto search = elapsed([&] {
        for (int q : data.queries) hits += std::find(container.begin(), container.end(), q) != container.end();
    });
    auto remove = elapsed([&] {
        for (int key : data.deletes) {
            auto it = std::find(container.begin(), container.end(), key);
            if (it != container.end()) container.erase(it);
        }
    });
    auto traverse = elapsed([&] { checksum = std::accumulate(container.begin(), container.end(), 0LL); });
    return {insert, search, remove, traverse, hits, checksum};
}

// Construct-validity supplement: std::forward_list is singly-linked, matching the
// custom Python SinglyLinkedList, unlike std::list (typically doubly-linked) used
// in run_linked above.
Result run_linked_fwd(const Dataset& data) {
    std::forward_list<int> container;
    i64 hits = 0, checksum = 0;
    auto insert = elapsed([&] { container.assign(data.values.begin(), data.values.end()); });
    auto search = elapsed([&] {
        for (int q : data.queries) hits += std::find(container.begin(), container.end(), q) != container.end();
    });
    auto remove = elapsed([&] {
        for (int key : data.deletes) {
            auto before = container.before_begin();
            auto it = container.begin();
            while (it != container.end() && *it != key) { ++before; ++it; }
            if (it != container.end()) container.erase_after(before);
        }
    });
    auto traverse = elapsed([&] { checksum = std::accumulate(container.begin(), container.end(), 0LL); });
    return {insert, search, remove, traverse, hits, checksum};
}

Result run_hash(const Dataset& data) {
    std::unordered_map<int, int> container;
    i64 hits = 0, checksum = 0;
    auto insert = elapsed([&] {
        container.reserve(data.values.size());
        for (int value : data.values) container.emplace(value, value);
    });
    auto search = elapsed([&] { for (int q : data.queries) hits += container.find(q) != container.end(); });
    auto remove = elapsed([&] { for (int key : data.deletes) container.erase(key); });
    auto traverse = elapsed([&] { for (const auto& entry : container) checksum += entry.first; });
    return {insert, search, remove, traverse, hits, checksum};
}

struct CalibratedResult { i64 batch_size, elapsed_ns, per_op_ns, hits, checksum; };

template <typename Function>
i64 time_batch(Function function, i64 batch) {
    auto start = Clock::now();
    for (i64 i = 0; i < batch; ++i) function();
    return std::chrono::duration_cast<std::chrono::nanoseconds>(Clock::now() - start).count();
}

template <typename Function>
i64 calibrate_batch_size(Function function, i64 threshold_ns) {
    i64 batch = 1;
    while (true) {
        i64 elapsed_ns = time_batch(function, batch);
        if (elapsed_ns >= threshold_ns || batch >= (1LL << 24)) return batch;
        batch *= 2;
    }
}

// Measurement-resolution supplement: array traversal and hash search were the
// two operations recorded near the clock's own tick granularity in the
// primary single-shot design (Section 3.4 measurement caveat) -- both are
// read-only and idempotent, so they can be repeated in a tight loop without
// rebuilding the container. Batches the operation until the timed interval
// clears a calibration threshold, then reports elapsed/batch as the
// per-operation estimate.
CalibratedResult run_calibrated(const std::string& structure, const std::string& operation, const Dataset& data, i64 threshold_ns) {
    volatile i64 sink = 0;
    if (structure == "array" && operation == "traverse") {
        std::vector<int> container = data.values;
        for (int key : data.deletes) {
            auto it = std::find(container.begin(), container.end(), key);
            if (it != container.end()) container.erase(it);
        }
        i64 checksum = std::accumulate(container.begin(), container.end(), 0LL);
        auto op = [&] { sink += std::accumulate(container.begin(), container.end(), 0LL); };
        i64 batch = calibrate_batch_size(op, threshold_ns);
        i64 elapsed_ns = time_batch(op, batch);
        return {batch, elapsed_ns, elapsed_ns / batch, 0, checksum};
    }
    if (structure == "hash" && operation == "search") {
        std::unordered_map<int, int> container;
        container.reserve(data.values.size());
        for (int value : data.values) container.emplace(value, value);
        i64 hits = 0;
        for (int q : data.queries) hits += container.find(q) != container.end();
        auto op = [&] { for (int q : data.queries) sink += container.find(q) != container.end(); };
        i64 batch = calibrate_batch_size(op, threshold_ns);
        i64 elapsed_ns = time_batch(op, batch);
        return {batch, elapsed_ns, elapsed_ns / batch, hits, 0};
    }
    throw std::runtime_error("Unsupported calibrated combination: " + structure + "/" + operation);
}

Result run_once(const std::string& structure, const Dataset& data) {
    if (structure == "array") return run_array(data);
    if (structure == "linked") return run_linked(data);
    if (structure == "linked_fwd") return run_linked_fwd(data);
    if (structure == "hash") return run_hash(data);
    throw std::runtime_error("Unknown structure: " + structure);
}

std::string filename(const std::string& path) {
    auto pos = path.find_last_of("/\\");
    return pos == std::string::npos ? path : path.substr(pos + 1);
}

int main(int argc, char** argv) {
    std::string dataset_path, structure, output_path, mode = "standard", operation;
    int warmups = 3, repeats = 10;
    i64 threshold_ns = 1'000'000; // 1 ms calibration threshold
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--dataset" && i + 1 < argc) dataset_path = argv[++i];
        else if (arg == "--structure" && i + 1 < argc) structure = argv[++i];
        else if (arg == "--warmups" && i + 1 < argc) warmups = std::stoi(argv[++i]);
        else if (arg == "--repeats" && i + 1 < argc) repeats = std::stoi(argv[++i]);
        else if (arg == "--output" && i + 1 < argc) output_path = argv[++i];
        else if (arg == "--mode" && i + 1 < argc) mode = argv[++i];
        else if (arg == "--operation" && i + 1 < argc) operation = argv[++i];
        else if (arg == "--threshold-ns" && i + 1 < argc) threshold_ns = std::stoll(argv[++i]);
    }
    if (dataset_path.empty() || structure.empty() || output_path.empty()) {
        std::cerr << "Required: --dataset PATH --structure NAME --output PATH\n";
        return 2;
    }
    try {
        Dataset data = load_dataset(dataset_path);
        if (mode == "calibrated") {
            if (operation.empty()) throw std::runtime_error("--mode calibrated requires --operation");
            for (int i = 0; i < warmups; ++i) run_calibrated(structure, operation, data, threshold_ns);
            std::ofstream output(output_path);
            output << "language,structure,dataset,n,operation,repeat,batch_size,elapsed_ns,per_op_ns,hits,checksum\n";
            for (int repeat = 0; repeat < repeats; ++repeat) {
                CalibratedResult r = run_calibrated(structure, operation, data, threshold_ns);
                output << "cpp," << structure << ',' << filename(dataset_path) << ',' << data.values.size() << ','
                       << operation << ',' << repeat << ',' << r.batch_size << ',' << r.elapsed_ns << ','
                       << r.per_op_ns << ',' << r.hits << ',' << r.checksum << '\n';
            }
            return 0;
        }
        for (int i = 0; i < warmups; ++i) run_once(structure, data);
        std::ofstream output(output_path);
        output << "language,structure,dataset,n,repeat,insert_ns,search_ns,delete_ns,traverse_ns,hits,checksum\n";
        for (int repeat = 0; repeat < repeats; ++repeat) {
            Result r = run_once(structure, data);
            output << "cpp," << structure << ',' << filename(dataset_path) << ',' << data.values.size() << ',' << repeat << ','
                   << r.insert_ns << ',' << r.search_ns << ',' << r.delete_ns << ',' << r.traverse_ns << ',' << r.hits << ',' << r.checksum << '\n';
        }
    } catch (const std::exception& error) {
        std::cerr << error.what() << '\n';
        return 1;
    }
}

