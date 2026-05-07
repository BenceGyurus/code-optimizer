from __future__ import annotations

from dataclasses import dataclass

from market_sim.data import Customer, Order


@dataclass(frozen=True)
class EnrichedOrder:
    order_id: int
    customer_id: int
    day: int
    amount: float
    discount: float
    net_amount: float
    channel: str
    sku: int
    quantity: int
    note: str
    segment: str
    region: str
    loyalty: int
    risk_band: int
    account_age: int


def enrich_orders(orders: list[Order], customers: list[Customer]) -> list[EnrichedOrder]:
    enriched: list[EnrichedOrder] = []
    for order in orders:
        matched = None
        for customer in customers:
            if customer.customer_id == order.customer_id:
                matched = customer
                break
        if matched is None:
            continue
        account_age = max(0, order.day - matched.signup_day)
        net_amount = order.amount * (1.0 - order.discount)
        enriched.append(
            EnrichedOrder(
                order.order_id,
                order.customer_id,
                order.day,
                order.amount,
                order.discount,
                net_amount,
                order.channel,
                order.sku,
                order.quantity,
                order.note,
                matched.segment,
                matched.region,
                matched.loyalty,
                matched.risk_band,
                account_age,
            )
        )
    return enriched


def customer_order_counts(enriched: list[EnrichedOrder]) -> dict[int, int]:
    counts: dict[int, int] = {}
    for order in enriched:
        counts[order.customer_id] = counts.get(order.customer_id, 0) + 1
    return counts
