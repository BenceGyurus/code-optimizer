from __future__ import annotations

from market_sim.data import Interaction
from market_sim.features import OrderFeature


def customer_base_scores(features: list[OrderFeature]) -> dict[int, float]:
    scores: dict[int, float] = {}
    counts: dict[int, int] = {}
    for feature in features:
        value = (
            feature.net_amount * 0.018
            + feature.segment_exposure * 0.002
            + feature.customer_recent_total * 0.004
            + feature.rolling_average * 0.011
        )
        scores[feature.customer_id] = scores.get(feature.customer_id, 0.0) + value
        counts[feature.customer_id] = counts.get(feature.customer_id, 0) + 1
    for customer_id, value in list(scores.items()):
        scores[customer_id] = value / max(1, counts.get(customer_id, 1))
    return scores


def network_influence(features: list[OrderFeature], interactions: list[Interaction]) -> dict[int, float]:
    base_scores = customer_base_scores(features)
    result: dict[int, float] = {}
    for customer_id, base in base_scores.items():
        incoming = 0.0
        outgoing = 0.0
        for interaction in interactions:
            if interaction.target_customer_id == customer_id:
                incoming += base_scores.get(interaction.source_customer_id, 0.0) * interaction.weight
            if interaction.source_customer_id == customer_id:
                outgoing += base_scores.get(interaction.target_customer_id, 0.0) * interaction.weight * 0.25
        result[customer_id] = base + incoming * 0.45 + outgoing
    return result


def regional_network_summary(features: list[OrderFeature], influence: dict[int, float]) -> dict[str, float]:
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    for feature in features:
        totals[feature.region] = totals.get(feature.region, 0.0) + influence.get(feature.customer_id, 0.0)
        counts[feature.region] = counts.get(feature.region, 0) + 1
    return {region: totals[region] / counts[region] for region in sorted(totals)}
