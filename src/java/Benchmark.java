import java.io.*;
import java.nio.file.*;
import java.util.*;

public final class Benchmark {
    record Dataset(int[] values, int[] queries, int[] deletes) {}
    record Result(long insertNs, long searchNs, long deleteNs, long traverseNs, long hits, long checksum) {}

    private static int[] parseLine(String line) {
        if (line.isBlank()) return new int[0];
        return Arrays.stream(line.trim().split("\\s+")).mapToInt(Integer::parseInt).toArray();
    }

    private static Dataset loadDataset(String path) throws IOException {
        List<String> lines = Files.readAllLines(Path.of(path));
        if (lines.size() != 3) throw new IllegalArgumentException("Dataset must contain exactly three lines");
        return new Dataset(parseLine(lines.get(0)), parseLine(lines.get(1)), parseLine(lines.get(2)));
    }

    private static Result runArray(Dataset d) {
        long start = System.nanoTime();
        ArrayList<Integer> c = new ArrayList<>(d.values.length);
        for (int value : d.values) c.add(value);
        long insert = System.nanoTime() - start;
        start = System.nanoTime();
        long hits = 0;
        for (int q : d.queries) if (c.contains(q)) hits++;
        long search = System.nanoTime() - start;
        start = System.nanoTime();
        for (int key : d.deletes) c.remove(Integer.valueOf(key));
        long delete = System.nanoTime() - start;
        start = System.nanoTime();
        long checksum = 0;
        for (int value : c) checksum += value;
        long traverse = System.nanoTime() - start;
        return new Result(insert, search, delete, traverse, hits, checksum);
    }

    private static Result runLinked(Dataset d) {
        long start = System.nanoTime();
        LinkedList<Integer> c = new LinkedList<>();
        for (int value : d.values) c.add(value);
        long insert = System.nanoTime() - start;
        start = System.nanoTime();
        long hits = 0;
        for (int q : d.queries) if (c.contains(q)) hits++;
        long search = System.nanoTime() - start;
        start = System.nanoTime();
        for (int key : d.deletes) c.remove(Integer.valueOf(key));
        long delete = System.nanoTime() - start;
        start = System.nanoTime();
        long checksum = 0;
        for (int value : c) checksum += value;
        long traverse = System.nanoTime() - start;
        return new Result(insert, search, delete, traverse, hits, checksum);
    }

    private static Result runHash(Dataset d) {
        long start = System.nanoTime();
        HashMap<Integer, Integer> c = new HashMap<>((int) (d.values.length / 0.75f) + 1);
        for (int value : d.values) c.put(value, value);
        long insert = System.nanoTime() - start;
        start = System.nanoTime();
        long hits = 0;
        for (int q : d.queries) if (c.containsKey(q)) hits++;
        long search = System.nanoTime() - start;
        start = System.nanoTime();
        for (int key : d.deletes) c.remove(key);
        long delete = System.nanoTime() - start;
        start = System.nanoTime();
        long checksum = 0;
        for (int key : c.keySet()) checksum += key;
        long traverse = System.nanoTime() - start;
        return new Result(insert, search, delete, traverse, hits, checksum);
    }

    private static Result runOnce(String structure, Dataset d) {
        return switch (structure) {
            case "array" -> runArray(d);
            case "linked" -> runLinked(d);
            case "hash" -> runHash(d);
            default -> throw new IllegalArgumentException("Unknown structure: " + structure);
        };
    }

    public static void main(String[] args) throws Exception {
        Map<String, String> options = new HashMap<>();
        for (int i = 0; i + 1 < args.length; i += 2) options.put(args[i], args[i + 1]);
        String datasetPath = options.get("--dataset");
        String structure = options.get("--structure");
        String outputPath = options.get("--output");
        int warmups = Integer.parseInt(options.getOrDefault("--warmups", "3"));
        int repeats = Integer.parseInt(options.getOrDefault("--repeats", "10"));
        if (datasetPath == null || structure == null || outputPath == null)
            throw new IllegalArgumentException("Required: --dataset PATH --structure NAME --output PATH");

        Dataset data = loadDataset(datasetPath);
        for (int i = 0; i < warmups; i++) runOnce(structure, data);
        Files.createDirectories(Path.of(outputPath).toAbsolutePath().getParent());
        try (PrintWriter out = new PrintWriter(Files.newBufferedWriter(Path.of(outputPath)))) {
            out.println("language,structure,dataset,n,repeat,insert_ns,search_ns,delete_ns,traverse_ns,hits,checksum");
            for (int repeat = 0; repeat < repeats; repeat++) {
                Result r = runOnce(structure, data);
                out.printf(Locale.ROOT, "java,%s,%s,%d,%d,%d,%d,%d,%d,%d,%d%n", structure,
                        Path.of(datasetPath).getFileName(), data.values.length, repeat, r.insertNs, r.searchNs,
                        r.deleteNs, r.traverseNs, r.hits, r.checksum);
            }
        }
    }
}

