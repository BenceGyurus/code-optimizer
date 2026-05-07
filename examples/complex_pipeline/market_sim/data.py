from __future__ import annotations

from dataclasses import dataclass


SEGMENTS = ("core", "growth", "enterprise", "public", "seasonal", "trial")
REGIONS = ("north", "east", "south", "west", "central")
CHANNELS = ("web", "retail", "partner", "field")
VOCABULARY = (
    "renewal",
    "upgrade",
    "discount",
    "support",
    "delivery",
    "priority",
    "trial",
    "invoice",
    "bundle",
    "migration",
    "training",
    "compliance",
)


@dataclass(frozen=True)
class Customer:
    customer_id: int
    segment: str
    region: str
    loyalty: int
    risk_band: int
    signup_day: int


@dataclass(frozen=True)
class Order:
    order_id: int
    customer_id: int
    day: int
    amount: float
    discount: float
    channel: str
    sku: int
    quantity: int
    note: str


@dataclass(frozen=True)
class Interaction:
    source_customer_id: int
    target_customer_id: int
    weight: float
    day: int


def make_dataset(order_count: int = 2800, customer_count: int = 460) -> dict[str, list]:
    customers = make_customers(customer_count)
    orders = make_orders(order_count, customer_count)
    interactions = make_interactions(customer_count)
    return {"customers": customers, "orders": orders, "interactions": interactions}


def make_customers(customer_count: int) -> list[Customer]:
    customers: list[Customer] = []
    for index in range(customer_count):
        segment = SEGMENTS[(index * 7 + index // 5) % len(SEGMENTS)]
        region = REGIONS[(index * 11 + 3) % len(REGIONS)]
        loyalty = (index * 17 + index // 3) % 100
        risk_band = (index * 13 + loyalty // 9) % 9
        signup_day = 1 + (index * 19) % 900
        customers.append(Customer(index, segment, region, loyalty, risk_band, signup_day))
    return customers


def make_orders(order_count: int, customer_count: int) -> list[Order]:
    orders: list[Order] = []
    for index in range(order_count):
        customer_id = (index * 37 + index // 4 + 11) % customer_count
        day = 1 + (index * 5 + customer_id * 3) % 730
        sku = (index * 23 + customer_id * 2) % 180
        quantity = 1 + ((index * 7 + sku) % 8)
        base = 18.0 + (sku % 31) * 1.75 + (customer_id % 13) * 0.8
        amount = round(base * quantity + ((index * index) % 97) * 0.13, 2)
        discount = round(((index * 3 + customer_id) % 18) / 100.0, 3)
        channel = CHANNELS[(index + customer_id) % len(CHANNELS)]
        note = make_note(index, customer_id, sku, channel)
        orders.append(Order(index, customer_id, day, amount, discount, channel, sku, quantity, note))
    orders.sort(key=lambda order: (order.day, order.order_id))
    return orders


def make_note(index: int, customer_id: int, sku: int, channel: str) -> str:
    words = [
        VOCABULARY[(index + customer_id) % len(VOCABULARY)],
        VOCABULARY[(index * 3 + sku) % len(VOCABULARY)],
        channel,
        VOCABULARY[(customer_id * 5 + sku) % len(VOCABULARY)],
    ]
    if index % 9 == 0:
        words.append("priority")
    if sku % 17 == 0:
        words.append("migration")
    if customer_id % 23 == 0:
        words.append("compliance")
    return " ".join(words)


def make_interactions(customer_count: int) -> list[Interaction]:
    interactions: list[Interaction] = []
    for source in range(customer_count):
        for offset in range(1, 5):
            target = (source * (offset + 3) + offset * 17) % customer_count
            if target == source:
                target = (target + 1) % customer_count
            weight = ((source + 11) * (offset + 5) % 29 + 1) / 30.0
            day = 1 + (source * 7 + offset * 13) % 730
            interactions.append(Interaction(source, target, weight, day))
    return interactions
