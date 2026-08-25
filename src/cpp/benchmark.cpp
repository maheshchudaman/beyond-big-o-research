#include <algorithm>
#include <chrono>
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

Result run_once(const std::string& structure, const Dataset& data) {
    if (structure == "array") return run_array(data);
    if (structure == "linked") return run_linked(data);
    if (structure == "hash") return run_hash(data);
    throw std::runtime_error("Unknown structure: " + structure);
}

std::string filename(const std::string& path) {
    auto pos = path.find_last_of("/\\");
    return pos == std::string::npos ? path : path.substr(pos + 1);
}

int main(int argc, char** argv) {
    std::string dataset_path, structure, output_path;
    int warmups = 3, repeats = 10;
    for (int i = 1; i < argc; ++i) {
        std::string arg = argv[i];
        if (arg == "--dataset" && i + 1 < argc) dataset_path = argv[++i];
        else if (arg == "--structure" && i + 1 < argc) structure = argv[++i];
        else if (arg == "--warmups" && i + 1 < argc) warmups = std::stoi(argv[++i]);
        else if (arg == "--repeats" && i + 1 < argc) repeats = std::stoi(argv[++i]);
        else if (arg == "--output" && i + 1 < argc) output_path = argv[++i];
    }
    if (dataset_path.empty() || structure.empty() || output_path.empty()) {
        std::cerr << "Required: --dataset PATH --structure NAME --output PATH\n";
        return 2;
    }
    try {
        Dataset data = load_dataset(dataset_path);
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

