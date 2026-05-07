from __future__ import annotations

import math

from market_sim.features import OrderFeature


def score_orders(
    features: list[OrderFeature],
    influence: dict[int, float],
    phrase_scores: dict[int, float],
    segment_text: dict[str, float],
) -> list[tuple[int, float]]:
    scored: list[tuple[int, float]] = []
    for feature in features:
        risk = influence.get(feature.customer_id, 0.0)
        text_score = segment_text.get(feature.segment, 0.0) * 0.003 + phrase_scores.get(feature.order_id, 0.0)
        amount_signal = math.log1p(feature.net_amount) * 2.1
        variability = math.sqrt(abs(feature.rolling_variance)) * 0.015
        exposure = math.log1p(max(0.0, feature.segment_exposure)) * 1.7
        recent = math.log1p(max(0.0, feature.customer_recent_total)) * 0.8
        pressure = math.log1p(max(0.0, feature.channel_pressure)) * 0.45
        score = amount_signal + variability + exposure + recent + pressure + risk * 0.12 + text_score
        if feature.region in {"north", "central"}:
            score *= 1.025
        if feature.segment in {"enterprise", "public"}:
            score += 0.75
        scored.append((feature.order_id, score))
    scored.sort(key=lambda item: (-item[1], item[0]))
    return scored


def bucket_scores(scored: list[tuple[int, float]]) -> dict[str, int]:
    buckets = {"low": 0, "medium": 0, "high": 0, "critical": 0}
    for _, score in scored:
        if score >= 32.0:
            buckets["critical"] += 1
        elif score >= 25.0:
            buckets["high"] += 1
        elif score >= 18.0:
            buckets["medium"] += 1
        else:
            buckets["low"] += 1
    return buckets


def checksum(scored: list[tuple[int, float]], buckets: dict[str, int], regional: dict[str, float]) -> int:
    total = 0
    for index, (order_id, score) in enumerate(scored[:180]):
        total = (total * 131 + order_id * 17 + int(score * 1000) + index) % 1_000_000_007
    for key in sorted(buckets):
        total = (total * 97 + buckets[key] * 19 + len(key)) % 1_000_000_007
    for key in sorted(regional):
        total = (total * 89 + int(regional[key] * 1000) + len(key)) % 1_000_000_007
    return total
