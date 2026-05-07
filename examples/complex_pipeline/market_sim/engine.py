from __future__ import annotations

import time

from market_sim.data import make_dataset
from market_sim.features import build_order_features
from market_sim.graph import network_influence, regional_network_summary
from market_sim.joins import enrich_orders
from market_sim.scoring import bucket_scores, checksum, score_orders
from market_sim.text import phrase_pressure, segment_text_scores


def run_pipeline(order_count: int = 2800, customer_count: int = 460) -> dict[str, object]:
    started = time.perf_counter()
    dataset = make_dataset(order_count=order_count, customer_count=customer_count)
    customers = dataset["customers"]
    orders = dataset["orders"]
    interactions = dataset["interactions"]

    enriched = enrich_orders(orders, customers)
    features = build_order_features(enriched)
    influence = network_influence(features, interactions)
    regional = regional_network_summary(features, influence)
    phrase_scores = phrase_pressure(enriched)
    segment_text = segment_text_scores(enriched)
    scored = score_orders(features, influence, phrase_scores, segment_text)
    buckets = bucket_scores(scored)
    elapsed = time.perf_counter() - started

    return {
        "orders": len(orders),
        "customers": len(customers),
        "enriched": len(enriched),
        "top_order": scored[0][0] if scored else None,
        "top_score": round(scored[0][1], 6) if scored else 0.0,
        "buckets": buckets,
        "regional": {key: round(value, 6) for key, value in regional.items()},
        "checksum": checksum(scored, buckets, regional),
        "elapsed_s": round(elapsed, 6),
    }
