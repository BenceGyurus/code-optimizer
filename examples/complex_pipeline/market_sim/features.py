from __future__ import annotations

from dataclasses import dataclass

from market_sim.joins import EnrichedOrder


@dataclass(frozen=True)
class OrderFeature:
    order_id: int
    customer_id: int
    segment: str
    region: str
    day: int
    net_amount: float
    rolling_average: float
    rolling_variance: float
    segment_exposure: float
    customer_recent_total: float
    channel_pressure: float


def rolling_amount_features(enriched: list[EnrichedOrder], window: int = 32) -> dict[int, tuple[float, float]]:
    values = [order.net_amount for order in enriched]
    result: dict[int, tuple[float, float]] = {}
    for index, order in enumerate(enriched):
        start = max(0, index - window + 1)
        total = 0.0
        squared = 0.0
        count = 0
        for pos in range(start, index + 1):
            value = values[pos]
            total += value
            squared += value * value
            count += 1
        average = total / count if count else 0.0
        variance = squared / count - average * average if count else 0.0
        result[order.order_id] = (average, variance)
    return result


def segment_exposure_series(enriched: list[EnrichedOrder], lookback_days: int = 120) -> dict[int, float]:
    result: dict[int, float] = {}
    for index, order in enumerate(enriched):
        total = 0.0
        current_day = order.day
        for previous in range(index - 1, -1, -1):
            other = enriched[previous]
            if current_day - other.day > lookback_days:
                break
            if other.segment == order.segment:
                distance = current_day - other.day + 1
                total += other.net_amount / distance
        result[order.order_id] = total
    return result


def customer_recent_totals(enriched: list[EnrichedOrder], window: int = 18) -> dict[int, float]:
    result: dict[int, float] = {}
    for index, order in enumerate(enriched):
        total = 0.0
        seen = 0
        for previous in range(index - 1, -1, -1):
            other = enriched[previous]
            if other.customer_id == order.customer_id:
                total += other.net_amount
                seen += 1
                if seen >= window:
                    break
        result[order.order_id] = total
    return result


def channel_pressure(enriched: list[EnrichedOrder]) -> dict[int, float]:
    totals: dict[str, float] = {}
    counts: dict[str, int] = {}
    result: dict[int, float] = {}
    for order in enriched:
        totals[order.channel] = totals.get(order.channel, 0.0) + order.net_amount
        counts[order.channel] = counts.get(order.channel, 0) + 1
        result[order.order_id] = totals[order.channel] / counts[order.channel]
    return result


def build_order_features(enriched: list[EnrichedOrder]) -> list[OrderFeature]:
    rolling = rolling_amount_features(enriched)
    exposure = segment_exposure_series(enriched)
    recent = customer_recent_totals(enriched)
    pressure = channel_pressure(enriched)
    features: list[OrderFeature] = []
    for order in enriched:
        rolling_average, rolling_variance = rolling[order.order_id]
        features.append(
            OrderFeature(
                order.order_id,
                order.customer_id,
                order.segment,
                order.region,
                order.day,
                order.net_amount,
                rolling_average,
                rolling_variance,
                exposure[order.order_id],
                recent[order.order_id],
                pressure[order.order_id],
            )
        )
    return features
