import pytest

from .complex_module import aggregate_sales, top_customers, normalize_names


def test_aggregate_sales_basic():
    rows = [
        {"category": "books", "price": 10.0, "quantity": 2, "discount": 3.0},
        {"category": "books", "price": 5.0, "quantity": 1, "discount": 0.0},
        {"category": "games", "price": 60.0, "quantity": 1, "discount": 10.0},
    ]
    by_category, grand_total = aggregate_sales(rows, 0.2)
    assert by_category == {"books": 22.0, "games": 50.0}
    assert grand_total == pytest.approx(86.4)


def test_aggregate_sales_negative_tax():
    with pytest.raises(ValueError):
        aggregate_sales([], -0.01)


def test_top_customers():
    orders = [
        {"customer": "A", "amounts": [10, 5, 5]},
        {"customer": "B", "amounts": [20]},
        {"customer": "A", "amounts": [3]},
        {"customer": "C", "amounts": [7, 8]},
    ]
    assert top_customers(orders, 2) == [("A", 23.0), ("B", 20.0)]


def test_top_customers_non_positive():
    assert top_customers([], 0) == []


def test_normalize_names():
    names = ["  Alice ", "alice", "Bob", "", "bob  ", "ALICE"]
    assert normalize_names(names) == ["alice", "bob"]
