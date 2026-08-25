PYTHON ?= python3

.PHONY: datasets build smoke benchmark analyse test validate clean

datasets:
	$(PYTHON) scripts/generate_datasets.py

build:
	mkdir -p build
	c++ -O2 -std=c++17 src/cpp/benchmark.cpp -o build/benchmark_cpp
	javac -d build src/java/Benchmark.java

smoke: datasets
	$(PYTHON) scripts/run_all.py --smoke

benchmark: datasets
	$(PYTHON) scripts/run_all.py

analyse:
	$(PYTHON) scripts/analyse_results.py

test:
	$(PYTHON) -m unittest discover -s tests -v

validate: test smoke
	$(PYTHON) scripts/analyse_results.py --input results/raw/smoke_combined.csv

clean:
	find build -type f -delete 2>/dev/null || true
