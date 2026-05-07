from __future__ import annotations

import unittest

from market_sim.data import make_dataset
from market_sim.engine import run_pipeline
from market_sim.features import build_order_features
from market_sim.graph import network_influence, regional_network_summary
from market_sim.joins import customer_order_counts, enrich_orders
from market_sim.scoring import bucket_scores, checksum, score_orders
from market_sim.text import phrase_pressure, segment_text_scores


class MarketSimTests(unittest.TestCase):
    def test_dataset_shape_is_stable(self) -> None:
        dataset = make_dataset(order_count=120, customer_count=35)
        self.assertEqual(len(dataset["customers"]), 35)
        self.assertEqual(len(dataset["orders"]), 120)
        self.assertEqual(len(dataset["interactions"]), 140)
        self.assertEqual(dataset["orders"][0].day, 34)

    def test_enrichment_keeps_all_orders(self) -> None:
        dataset = make_dataset(order_count=180, customer_count=40)
        enriched = enrich_orders(dataset["orders"], dataset["customers"])
        counts = customer_order_counts(enriched)
        self.assertEqual(len(enriched), 180)
        self.assertEqual(sum(counts.values()), 180)
        self.assertTrue(all(order.segment for order in enriched))

    def test_feature_building_is_deterministic(self) -> None:
        dataset = make_dataset(order_count=220, customer_count=50)
        enriched = enrich_orders(dataset["orders"], dataset["customers"])
        features = build_order_features(enriched)
        self.assertEqual(len(features), len(enriched))
        self.assertAlmostEqual(features[0].rolling_average, features[0].net_amount)
        self.assertGreater(sum(feature.segment_exposure for feature in features), 0.0)

    def test_graph_and_text_scores_are_non_empty(self) -> None:
        dataset = make_dataset(order_count=240, customer_count=55)
        enriched = enrich_orders(dataset["orders"], dataset["customers"])
        features = build_order_features(enriched)
        influence = network_influence(features, dataset["interactions"])
        regional = regional_network_summary(features, influence)
        phrases = phrase_pressure(enriched)
        text_scores = segment_text_scores(enriched)
        self.assertGreater(len(influence), 0)
        self.assertEqual(set(regional), {"central", "east", "north", "south", "west"})
        self.assertEqual(len(phrases), len(enriched))
        self.assertIn("enterprise", text_scores)

    def test_pipeline_checksum_is_stable_small(self) -> None:
        result = run_pipeline(order_count=320, customer_count=70)
        self.assertEqual(result["checksum"], 516622358)
        self.assertEqual(result["top_order"], 27)
        self.assertEqual(result["buckets"], {"critical": 209, "high": 100, "low": 4, "medium": 7})

    def test_manual_pipeline_matches_engine_checksum(self) -> None:
        dataset = make_dataset(order_count=260, customer_count=60)
        enriched = enrich_orders(dataset["orders"], dataset["customers"])
        features = build_order_features(enriched)
        influence = network_influence(features, dataset["interactions"])
        regional = regional_network_summary(features, influence)
        phrases = phrase_pressure(enriched)
        text_scores = segment_text_scores(enriched)
        scored = score_orders(features, influence, phrases, text_scores)
        buckets = bucket_scores(scored)
        self.assertEqual(checksum(scored, buckets, regional), 787694887)


if __name__ == "__main__":
    unittest.main()
