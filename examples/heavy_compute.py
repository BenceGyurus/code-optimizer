import argparse
import random
import time
import unittest


def matrix_multiply(a, b):
    """Multiply two dense matrices represented as nested lists."""
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


def moving_average_slow(values, window):
    """Return fixed-width moving averages."""
    if window <= 0:
        raise ValueError("window must be positive")
    if window > len(values):
        return []

    averages = []
    for index in range(len(values) - window + 1):
        total = 0.0
        for offset in range(window):
            total += values[index + offset]
        averages.append(total / window)
    return averages


def join_events_to_users_slow(events, users):
    """Attach user names to event records."""
    joined = []
    for event in events:
        user_name = "unknown"
        for user in users:
            if user["id"] == event["user_id"]:
                user_name = user["name"]
                break
        joined.append(
            {
                "event_id": event["event_id"],
                "user_id": event["user_id"],
                "user_name": user_name,
                "amount": event["amount"],
                "category": event["category"],
            }
        )
    return joined


def category_totals_slow(records, categories):
    """Return totals and counts for the requested categories."""
    totals = {}
    for category in categories:
        total = 0
        count = 0
        for record in records:
            if record["category"] == category:
                total += record["amount"]
                count += 1
        totals[category] = {"total": total, "count": count}
    return totals


def heat_diffusion_slow(grid, passes):
    """Run repeated 5-point grid diffusion passes."""
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
                next_grid[y][x] = sum(neighbors) / len(neighbors)
        current = next_grid
    return current


def branchy_event_score_slow(records):
    """Compute a deterministic score for event records."""
    total = 0
    for record in records:
        amount = record["amount"]
        category = record["category"]
        user_id = record["user_id"]

        if amount < 50:
            total += amount * 3 + user_id % 7
        elif amount < 100:
            total += amount * 2 - user_id % 5
        elif amount < 200:
            if category.endswith("0") or category.endswith("5"):
                total += amount + 17
            else:
                total += amount - 11
        elif amount < 350:
            if user_id % 2 == 0:
                total += amount // 3
            else:
                total += amount // 5
        else:
            if category < "category-040":
                total += amount * 4
            else:
                total += amount * 2
    return total


def rolling_volatility_slow(values, window):
    """Return per-window mean and variance pairs."""
    if window <= 0:
        raise ValueError("window must be positive")
    if window > len(values):
        return []

    output = []
    for start in range(len(values) - window + 1):
        mean = 0.0
        for offset in range(window):
            mean += values[start + offset]
        mean /= window

        variance = 0.0
        for offset in range(window):
            delta = values[start + offset] - mean
            variance += delta * delta
        output.append((mean, variance / window))
    return output


def column_energy_slow(matrix):
    """Return a deterministic energy value for each matrix column."""
    if not matrix or not matrix[0]:
        return []

    height = len(matrix)
    width = len(matrix[0])
    energies = []
    for column in range(width):
        total = 0.0
        for row in range(height):
            value = matrix[row][column]
            total += value * value + (row % 5) * 0.001
        energies.append(total)
    return energies


def segmented_prefix_sums_slow(records):
    """Return category-local prefix totals in input order."""
    prefixes = []
    for index, record in enumerate(records):
        running = 0
        category = record["category"]
        for previous in range(index + 1):
            candidate = records[previous]
            if candidate["category"] == category:
                running += candidate["amount"]
        prefixes.append(
            {
                "event_id": record["event_id"],
                "category": category,
                "prefix_total": running,
            }
        )
    return prefixes


def token_frequency_slow(records):
    """Build a token frequency map from event-like records."""
    counts = {}
    for record in records:
        sentence = (
            f"{record['category']} {record['user_name']} amount {record['amount']} "
            f"bucket {record['amount'] // 10}"
        )
        for token in sentence.lower().replace("-", " ").split():
            counts[token] = counts.get(token, 0) + 1
    return counts


def sparse_bucket_updates_slow(records, bucket_count):
    """Apply deterministic sparse bucket updates."""
    buckets = [0] * bucket_count
    for record in records:
        amount = record["amount"]
        category_value = int(record["category"].split("-")[1])
        base = (record["user_id"] * 131 + amount * 17 + category_value) % bucket_count
        for step in range(4):
            index = (base + step * step + category_value) % bucket_count
            if (amount + step) % 3 == 0:
                buckets[index] += amount // (step + 1)
            else:
                buckets[index] -= (amount + category_value) % (step + 5)
    return buckets


def pairwise_distance_histogram_slow(points, bins, scale):
    """Build a histogram from pairwise point distances."""
    histogram = [0] * bins
    for index, (x1, y1) in enumerate(points):
        for other in range(index + 1, len(points)):
            x2, y2 = points[other]
            dx = x1 - x2
            dy = y1 - y2
            distance = (dx * dx + dy * dy) ** 0.5
            bucket = int(distance * scale)
            if bucket >= bins:
                bucket = bins - 1
            histogram[bucket] += 1
    return histogram


def generate_matrix(size, seed):
    rng = random.Random(seed)
    return [[rng.random() for _ in range(size)] for _ in range(size)]


def generate_users(count):
    return [{"id": user_id, "name": f"user-{user_id:05d}"} for user_id in range(count)]


def generate_events(count, user_count, category_count, seed):
    rng = random.Random(seed)
    categories = [f"category-{index:03d}" for index in range(category_count)]
    events = []
    for event_id in range(count):
        events.append(
            {
                "event_id": event_id,
                "user_id": rng.randrange(user_count),
                "amount": rng.randrange(1, 500),
                "category": categories[rng.randrange(category_count)],
            }
        )
    return events, categories


def generate_points(count, seed):
    rng = random.Random(seed)
    return [(rng.random() * 100.0, rng.random() * 100.0) for _ in range(count)]


def workload(matrix_size=90, event_count=12000, user_count=1200, category_count=80):
    a = generate_matrix(matrix_size, 101)
    b = generate_matrix(matrix_size, 202)
    product = matrix_multiply(a, b)
    diffusion = heat_diffusion_slow(product, 3)
    column_energies = column_energy_slow(diffusion)

    values = [((index * 17) % 1000) / 7.0 for index in range(event_count)]
    averages = moving_average_slow(values, 64)
    volatility = rolling_volatility_slow(values, 48)

    users = generate_users(user_count)
    events, categories = generate_events(event_count, user_count, category_count, 303)
    joined = join_events_to_users_slow(events, users)
    totals = category_totals_slow(joined, categories)
    branch_score = branchy_event_score_slow(joined)
    prefixes = segmented_prefix_sums_slow(joined)
    token_counts = token_frequency_slow(joined)
    bucket_updates = sparse_bucket_updates_slow(joined, 257)
    points = generate_points(min(max(matrix_size * 3, 24), 220), 404)
    distance_histogram = pairwise_distance_histogram_slow(points, bins=32, scale=0.4)

    return checksum(
        product,
        diffusion,
        column_energies,
        averages,
        volatility,
        joined,
        totals,
        branch_score,
        prefixes,
        token_counts,
        bucket_updates,
        distance_histogram,
    )


def checksum(
    product,
    diffusion,
    column_energies,
    averages,
    volatility,
    joined,
    totals,
    branch_score,
    prefixes,
    token_counts,
    bucket_updates,
    distance_histogram,
):
    matrix_part = int(sum(sum(row) for row in product) * 1000) % 1_000_000_007
    diffusion_part = int(sum(sum(row) for row in diffusion) * 1000) % 1_000_000_007
    energy_part = int(sum(column_energies) * 1000) % 1_000_000_007
    average_part = int(sum(averages) * 1000) % 1_000_000_007
    volatility_part = int(sum(mean + variance for mean, variance in volatility) * 1000) % 1_000_000_007
    joined_part = sum((record["event_id"] + 1) * (record["amount"] + 3) for record in joined) % 1_000_000_007
    total_part = sum((index + 1) * value["total"] for index, value in enumerate(totals.values())) % 1_000_000_007
    branch_part = branch_score % 1_000_000_007
    prefix_part = sum((index + 1) * item["prefix_total"] for index, item in enumerate(prefixes)) % 1_000_000_007
    token_part = sum((len(token) + 1) * count for token, count in sorted(token_counts.items())) % 1_000_000_007
    bucket_part = sum((index + 3) * value for index, value in enumerate(bucket_updates)) % 1_000_000_007
    histogram_part = sum((index + 5) * value for index, value in enumerate(distance_histogram)) % 1_000_000_007
    return (
        matrix_part
        + diffusion_part
        + energy_part
        + average_part
        + volatility_part
        + joined_part
        + total_part
        + branch_part
        + prefix_part
        + token_part
        + bucket_part
        + histogram_part
    ) % 1_000_000_007


def run_benchmark(matrix_size=90, event_count=12000, repetitions=1):
    best = None
    last_checksum = None
    for run_index in range(repetitions):
        start = time.perf_counter()
        last_checksum = workload(matrix_size=matrix_size, event_count=event_count)
        duration = time.perf_counter() - start
        best = duration if best is None else min(best, duration)
        print(f"run={run_index + 1} seconds={duration:.6f} checksum={last_checksum}")
    print(f"best_seconds={best:.6f} checksum={last_checksum}")
    return best, last_checksum


class TestHeavyCompute(unittest.TestCase):
    def test_matrix_multiply(self):
        a = [[1.0, 2.0], [3.0, 4.0]]
        b = [[5.0, 6.0], [7.0, 8.0]]
        self.assertEqual(matrix_multiply(a, b), [[19.0, 22.0], [43.0, 50.0]])

    def test_moving_average(self):
        self.assertEqual(moving_average_slow([1, 2, 3, 4, 5], 3), [2.0, 3.0, 4.0])

    def test_join_events_to_users(self):
        users = [{"id": 1, "name": "Ada"}, {"id": 2, "name": "Linus"}]
        events = [{"event_id": 10, "user_id": 2, "amount": 7, "category": "x"}]
        joined = join_events_to_users_slow(events, users)
        self.assertEqual(joined[0]["user_name"], "Linus")

    def test_category_totals(self):
        records = [
            {"category": "a", "amount": 2},
            {"category": "b", "amount": 5},
            {"category": "a", "amount": 3},
        ]
        self.assertEqual(
            category_totals_slow(records, ["a", "b"]),
            {"a": {"total": 5, "count": 2}, "b": {"total": 5, "count": 1}},
        )

    def test_heat_diffusion(self):
        grid = [
            [1.0, 2.0, 3.0],
            [4.0, 5.0, 6.0],
            [7.0, 8.0, 9.0],
        ]
        self.assertEqual(
            heat_diffusion_slow(grid, 1),
            [
                [2.3333333333333335, 2.75, 3.6666666666666665],
                [4.25, 5.0, 5.75],
                [6.333333333333333, 7.25, 7.666666666666667],
            ],
        )

    def test_branchy_event_score(self):
        joined = [
            {"event_id": 1, "user_id": 4, "amount": 20, "category": "category-010"},
            {"event_id": 2, "user_id": 3, "amount": 120, "category": "category-012"},
            {"event_id": 3, "user_id": 8, "amount": 380, "category": "category-050"},
        ]
        self.assertEqual(branchy_event_score_slow(joined), 933)

    def test_rolling_volatility(self):
        self.assertEqual(
            rolling_volatility_slow([1.0, 2.0, 3.0, 4.0], 2),
            [(1.5, 0.25), (2.5, 0.25), (3.5, 0.25)],
        )

    def test_column_energy(self):
        matrix = [[1.0, 2.0], [3.0, 4.0]]
        actual = column_energy_slow(matrix)
        self.assertAlmostEqual(actual[0], 10.001)
        self.assertAlmostEqual(actual[1], 20.001)

    def test_segmented_prefix_sums(self):
        records = [
            {"event_id": 1, "category": "a", "amount": 2},
            {"event_id": 2, "category": "b", "amount": 5},
            {"event_id": 3, "category": "a", "amount": 3},
        ]
        self.assertEqual(
            segmented_prefix_sums_slow(records),
            [
                {"event_id": 1, "category": "a", "prefix_total": 2},
                {"event_id": 2, "category": "b", "prefix_total": 5},
                {"event_id": 3, "category": "a", "prefix_total": 5},
            ],
        )

    def test_token_frequency(self):
        records = [
            {"user_name": "Ada", "amount": 20, "category": "category-010"},
            {"user_name": "Ada", "amount": 25, "category": "category-010"},
        ]
        self.assertEqual(
            token_frequency_slow(records),
            {"category": 2, "010": 2, "ada": 2, "amount": 2, "20": 1, "25": 1, "bucket": 2, "2": 2},
        )

    def test_sparse_bucket_updates(self):
        records = [
            {"user_id": 1, "amount": 10, "category": "category-002"},
            {"user_id": 2, "amount": 11, "category": "category-003"},
        ]
        self.assertEqual(
            sparse_bucket_updates_slow(records, 16),
            [-6, -2, 0, 0, 0, 3, 0, -4, 5, 0, -4, 0, 0, 0, 0, 0],
        )

    def test_pairwise_distance_histogram(self):
        points = [(0.0, 0.0), (3.0, 4.0), (6.0, 8.0)]
        self.assertEqual(pairwise_distance_histogram_slow(points, bins=6, scale=0.5), [0, 0, 2, 0, 0, 1])

    def test_workload_checksum_is_stable(self):
        self.assertEqual(workload(matrix_size=8, event_count=200, user_count=30, category_count=8), 366047001)


def run_tests():
    suite = unittest.TestLoader().loadTestsFromTestCase(TestHeavyCompute)
    return unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful()


def parse_args():
    parser = argparse.ArgumentParser(description="Intentionally slow deterministic optimization target.")
    parser.add_argument("--matrix-size", type=int, default=90)
    parser.add_argument("--events", type=int, default=12000)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--skip-tests", action="store_true")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.skip_tests or run_tests():
        run_benchmark(matrix_size=args.matrix_size, event_count=args.events, repetitions=args.repetitions)
