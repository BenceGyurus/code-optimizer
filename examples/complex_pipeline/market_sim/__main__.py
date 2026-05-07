from __future__ import annotations

import argparse
import json
import unittest

from market_sim.engine import run_pipeline


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--skip-tests", action="store_true")
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--orders", type=int, default=5200)
    parser.add_argument("--customers", type=int, default=760)
    return parser.parse_args()


def run_tests() -> None:
    suite = unittest.defaultTestLoader.discover(".", pattern="test_*.py")
    result = unittest.TextTestRunner(verbosity=1).run(suite)
    if not result.wasSuccessful():
        raise SystemExit(1)


def main() -> int:
    args = parse_args()
    if not args.skip_tests:
        run_tests()

    result = None
    for _ in range(max(1, args.repetitions)):
        result = run_pipeline(order_count=args.orders, customer_count=args.customers)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
