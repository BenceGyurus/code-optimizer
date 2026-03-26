from typing import List, Dict, Tuple




def aggregate_sales(rows: List[Dict[str, object]], tax_rate: float) -> Tuple[Dict[str, float], float]:
    if tax_rate < 0:
        raise ValueError("tax_rate must be non-negative")

    by_category: Dict[str, float] = {}
    total = 0.0

    for row in rows:
        category = str(row.get("category", "unknown"))
        price = float(row.get("price", 0.0))
        quantity = int(row.get("quantity", 1))
        discount = float(row.get("discount", 0.0))

        subtotal = price * quantity - discount
        by_category[category] = by_category.get(category, 0.0) + subtotal
        total += subtotal

    tax = total * tax_rate
    grand_total = total + tax
    return by_category, grand_total


def top_customers(orders: List[Dict[str, object]], top_n: int) -> List[Tuple[str, float]]:
    if top_n <= 0:
        return []

    totals: Dict[str, float] = {}
    for order in orders:
        customer = str(order.get("customer", "unknown"))
        amounts = order.get("amounts", [])
        order_total = sum(float(amount) for amount in amounts)
        totals[customer] = totals.get(customer, 0.0) + order_total

    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    return ranked[:top_n]


def normalize_names(names: List[str]) -> List[str]:
    normalized: List[str] = []
    seen = set()
    for name in names:
        cleaned = name.strip().lower()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            normalized.append(cleaned)
    return normalized
