import argparse
import random
import time
import unittest


def matrix_chain_accumulate_slow(a, b):
    rows_a = len(a)
    cols_a = len(a[0])
    rows_b = len(b)
    cols_b = len(b[0])
    if cols_a != rows_b:
        raise ValueError("Incompatible dimensions")
    result = [[0.0 for _ in range(cols_b)] for _ in range(rows_a)]
    for i in range(rows_a):
        for j in range(cols_b):
            total = 0.0
            for k in range(cols_a):
                total += a[i][k] * b[k][j]
            result[i][j] = total
    return result


def window_stats_slow(values, window):
    if window <= 0:
        raise ValueError("window must be positive")
    if window > len(values):
        return []
    output = []
    for start in range(len(values) - window + 1):
        total = 0.0
        for offset in range(window):
            total += values[start + offset]
        mean = total / window
        variance = 0.0
        for offset in range(window):
            delta = values[start + offset] - mean
            variance += delta * delta
        output.append((mean, variance / window))
    return output


def join_sensor_batches_slow(batches, sensors, zones):
    joined = []
    for batch in batches:
        sensor_name = "unknown"
        zone_name = "unknown"
        zone_weight = 0
        for sensor in sensors:
            if sensor["id"] == batch["sensor_id"]:
                sensor_name = sensor["name"]
                for zone in zones:
                    if zone["id"] == sensor["zone_id"]:
                        zone_name = zone["name"]
                        zone_weight = zone["weight"]
                        break
                break
        joined.append(
            {
                "batch_id": batch["batch_id"],
                "sensor_id": batch["sensor_id"],
                "sensor_name": sensor_name,
                "zone_name": zone_name,
                "zone_weight": zone_weight,
                "value": batch["value"],
                "bucket": batch["bucket"],
            }
        )
    return joined


def category_prefix_sums_slow(records):
    prefixes = []
    for index, record in enumerate(records):
        running = 0
        bucket = record["bucket"]
        for previous in range(index + 1):
            candidate = records[previous]
            if candidate["bucket"] == bucket:
                running += candidate["value"]
        prefixes.append(
            {
                "batch_id": record["batch_id"],
                "bucket": bucket,
                "prefix_total": running,
            }
        )
    return prefixes


def heat_relaxation_slow(grid, passes):
    height = len(grid)
    width = len(grid[0])
    current = [row[:] for row in grid]
    for _ in range(passes):
        next_grid = [[0.0 for _ in range(width)] for _ in range(height)]
        for y in range(height):
            for x in range(width):
                neighbors = [current[y][x]]
                if y > 0:
                    neighbors.append(current[y - 1][x])
                if y + 1 < height:
                    neighbors.append(current[y + 1][x])
                if x > 0:
                    neighbors.append(current[y][x - 1])
                if x + 1 < width:
                    neighbors.append(current[y][x + 1])
                if y > 0 and x > 0:
                    neighbors.append(current[y - 1][x - 1])
                if y > 0 and x + 1 < width:
                    neighbors.append(current[y - 1][x + 1])
                if y + 1 < height and x > 0:
                    neighbors.append(current[y + 1][x - 1])
                if y + 1 < height and x + 1 < width:
                    neighbors.append(current[y + 1][x + 1])
                next_grid[y][x] = sum(neighbors) / len(neighbors)
        current = next_grid
    return current


def column_pair_products_slow(matrix):
    if not matrix or not matrix[0]:
        return []
    height = len(matrix)
    width = len(matrix[0])
    products = [[0.0 for _ in range(width)] for _ in range(width)]
    for left in range(width):
        for right in range(width):
            total = 0.0
            for row in range(height):
                total += matrix[row][left] * matrix[row][right]
            products[left][right] = total
    return products


def token_pair_counts_slow(records):
    counts = {}
    for record in records:
        sentence = (
            f"{record['sensor_name']} {record['zone_name']} bucket {record['bucket']} "
            f"value {record['value']} weight {record['zone_weight']}"
        )
        tokens = sentence.lower().replace("-", " ").split()
        for index in range(len(tokens) - 1):
            pair = (tokens[index], tokens[index + 1])
            counts[pair] = counts.get(pair, 0) + 1
    return counts


def ring_bucket_updates_slow(records, bucket_count):
    buckets = [0] * bucket_count
    for record in records:
        value = record["value"]
        base = (record["sensor_id"] * 97 + record["zone_weight"] * 13 + value * 7) % bucket_count
        for step in range(6):
            index = (base + step * step + record["bucket"]) % bucket_count
            if (value + step + record["zone_weight"]) % 4 == 0:
                buckets[index] += value // (step + 1)
            elif (value + step) % 3 == 0:
                buckets[index] -= (value + record["bucket"]) % (step + 5)
            else:
                buckets[index] += (value * (step + 2) + record["zone_weight"]) % 17
    return buckets


def band_energy_slow(matrix, band_width):
    height = len(matrix)
    width = len(matrix[0])
    energies = [0.0 for _ in range(width)]
    for column in range(width):
        total = 0.0
        start = 0 if column < band_width else column - band_width
        end = width if column + band_width + 1 > width else column + band_width + 1
        for neighbor in range(start, end):
            for row in range(height):
                total += matrix[row][column] * matrix[row][neighbor]
        energies[column] = total
    return energies


def generate_matrix(size, seed):
    rng = random.Random(seed)
    return [[rng.random() for _ in range(size)] for _ in range(size)]


def generate_zones(count):
    return [{"id": zone_id, "name": f"zone-{zone_id:03d}", "weight": (zone_id * 7) % 19 + 1} for zone_id in range(count)]


def generate_sensors(count, zone_count):
    sensors = []
    for sensor_id in range(count):
        sensors.append({"id": sensor_id, "name": f"sensor-{sensor_id:05d}", "zone_id": sensor_id % zone_count})
    return sensors


def generate_batches(count, sensor_count, bucket_count, seed):
    rng = random.Random(seed)
    batches = []
    for batch_id in range(count):
        batches.append(
            {
                "batch_id": batch_id,
                "sensor_id": rng.randrange(sensor_count),
                "value": rng.randrange(1, 1000),
                "bucket": rng.randrange(bucket_count),
            }
        )
    return batches


def workload(matrix_size=84, batch_count=18000, sensor_count=1600, zone_count=64, bucket_count=96):
    a = generate_matrix(matrix_size, 111)
    b = generate_matrix(matrix_size, 222)
    product = matrix_chain_accumulate_slow(a, b)
    relaxed = heat_relaxation_slow(product, 3)
    pair_products = column_pair_products_slow(relaxed)
    band_energies = band_energy_slow(relaxed, 5)

    values = [((index * 29) % 2000) / 11.0 for index in range(batch_count)]
    stats = window_stats_slow(values, 96)

    zones = generate_zones(zone_count)
    sensors = generate_sensors(sensor_count, zone_count)
    batches = generate_batches(batch_count, sensor_count, bucket_count, 333)
    joined = join_sensor_batches_slow(batches, sensors, zones)
    prefixes = category_prefix_sums_slow(joined)
    token_pairs = token_pair_counts_slow(joined)
    ring_updates = ring_bucket_updates_slow(joined, 509)

    return checksum(product, relaxed, pair_products, band_energies, stats, joined, prefixes, token_pairs, ring_updates)


def checksum(product, relaxed, pair_products, band_energies, stats, joined, prefixes, token_pairs, ring_updates):
    product_part = int(sum(sum(row) for row in product) * 1000) % 1_000_000_007
    relaxed_part = int(sum(sum(row) for row in relaxed) * 1000) % 1_000_000_007
    pair_part = int(sum(sum(row) for row in pair_products) * 1000) % 1_000_000_007
    energy_part = int(sum(band_energies) * 1000) % 1_000_000_007
    stats_part = int(sum(mean + variance for mean, variance in stats) * 1000) % 1_000_000_007
    joined_part = sum((record["batch_id"] + 1) * (record["value"] + 3) for record in joined) % 1_000_000_007
    prefix_part = sum((index + 1) * item["prefix_total"] for index, item in enumerate(prefixes)) % 1_000_000_007
    token_part = sum((len(left) + len(right) + 1) * count for (left, right), count in sorted(token_pairs.items())) % 1_000_000_007
    ring_part = sum((index + 5) * value for index, value in enumerate(ring_updates)) % 1_000_000_007
    return (
        product_part
        + relaxed_part
        + pair_part
        + energy_part
        + stats_part
        + joined_part
        + prefix_part
        + token_part
        + ring_part
    ) % 1_000_000_007


def run_benchmark(matrix_size=84, batch_count=18000, repetitions=1):
    best = None
    last_checksum = None
    for run_index in range(repetitions):
        start = time.perf_counter()
        last_checksum = workload(matrix_size=matrix_size, batch_count=batch_count)
        duration = time.perf_counter() - start
        best = duration if best is None else min(best, duration)
        print(f"run={run_index + 1} seconds={duration:.6f} checksum={last_checksum}")
    print(f"best_seconds={best:.6f} checksum={last_checksum}")
    return best, last_checksum


class TestExtremeCompute(unittest.TestCase):
    def test_matrix_chain_accumulate(self):
        a = [[1.0, 2.0], [3.0, 4.0]]
        b = [[5.0, 6.0], [7.0, 8.0]]
        self.assertEqual(matrix_chain_accumulate_slow(a, b), [[19.0, 22.0], [43.0, 50.0]])

    def test_window_stats(self):
        self.assertEqual(window_stats_slow([1.0, 2.0, 3.0, 4.0], 2), [(1.5, 0.25), (2.5, 0.25), (3.5, 0.25)])

    def test_join_sensor_batches(self):
        zones = [{"id": 0, "name": "zone-a", "weight": 3}]
        sensors = [{"id": 1, "name": "sensor-a", "zone_id": 0}]
        batches = [{"batch_id": 7, "sensor_id": 1, "value": 9, "bucket": 2}]
        joined = join_sensor_batches_slow(batches, sensors, zones)
        self.assertEqual(joined[0]["sensor_name"], "sensor-a")
        self.assertEqual(joined[0]["zone_name"], "zone-a")

    def test_category_prefix_sums(self):
        records = [
            {"batch_id": 1, "bucket": 2, "value": 4},
            {"batch_id": 2, "bucket": 1, "value": 5},
            {"batch_id": 3, "bucket": 2, "value": 7},
        ]
        self.assertEqual(
            category_prefix_sums_slow(records),
            [
                {"batch_id": 1, "bucket": 2, "prefix_total": 4},
                {"batch_id": 2, "bucket": 1, "prefix_total": 5},
                {"batch_id": 3, "bucket": 2, "prefix_total": 11},
            ],
        )

    def test_heat_relaxation(self):
        grid = [[1.0, 2.0], [3.0, 4.0]]
        self.assertEqual(heat_relaxation_slow(grid, 1), [[2.5, 2.5], [2.5, 2.5]])

    def test_column_pair_products(self):
        matrix = [[1.0, 2.0], [3.0, 4.0]]
        self.assertEqual(column_pair_products_slow(matrix), [[10.0, 14.0], [14.0, 20.0]])

    def test_token_pair_counts(self):
        records = [{"sensor_name": "S1", "zone_name": "Z1", "bucket": 2, "value": 7, "zone_weight": 3}]
        self.assertEqual(
            token_pair_counts_slow(records),
            {
                ("s1", "z1"): 1,
                ("z1", "bucket"): 1,
                ("bucket", "2"): 1,
                ("2", "value"): 1,
                ("value", "7"): 1,
                ("7", "weight"): 1,
                ("weight", "3"): 1,
            },
        )

    def test_ring_bucket_updates(self):
        records = [{"sensor_id": 1, "zone_weight": 2, "value": 9, "bucket": 3}]
        self.assertEqual(ring_bucket_updates_slow(records, 16), [0, 4, 0, 0, 0, 0, -3, 0, 0, 0, 0, 0, 0, 3, 4, 0])

    def test_band_energy(self):
        matrix = [[1.0, 2.0], [3.0, 4.0]]
        self.assertEqual(band_energy_slow(matrix, 1), [24.0, 34.0])

    def test_workload_checksum_is_stable(self):
        self.assertEqual(workload(matrix_size=8, batch_count=240, sensor_count=40, zone_count=8, bucket_count=10), 693109915)


def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestExtremeCompute)
    return unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful()


def parse_args():
    parser = argparse.ArgumentParser(description="Large deterministic optimization target.")
    parser.add_argument("--matrix-size", type=int, default=84)
    parser.add_argument("--batches", type=int, default=18000)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--skip-tests", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.skip_tests or run_tests():
        run_benchmark(matrix_size=args.matrix_size, batch_count=args.batches, repetitions=args.repetitions)
