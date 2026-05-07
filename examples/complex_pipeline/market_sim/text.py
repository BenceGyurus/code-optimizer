from __future__ import annotations

from market_sim.joins import EnrichedOrder


IMPORTANT_TERMS = ("priority", "migration", "compliance", "discount", "support", "renewal")


def note_term_matrix(enriched: list[EnrichedOrder]) -> dict[str, dict[str, int]]:
    matrix: dict[str, dict[str, int]] = {}
    for order in enriched:
        segment_counts = matrix.setdefault(order.segment, {term: 0 for term in IMPORTANT_TERMS})
        tokens = order.note.lower().split()
        for term in IMPORTANT_TERMS:
            for token in tokens:
                if token == term:
                    segment_counts[term] += 1
    return matrix


def phrase_pressure(enriched: list[EnrichedOrder]) -> dict[int, float]:
    result: dict[int, float] = {}
    for index, order in enumerate(enriched):
        score = 0.0
        tokens = order.note.lower().split()
        for previous in range(max(0, index - 50), index):
            other_tokens = enriched[previous].note.lower().split()
            overlap = 0
            for token in tokens:
                if token in other_tokens:
                    overlap += 1
            if overlap:
                score += overlap / (index - previous + 1)
        result[order.order_id] = score
    return result


def segment_text_scores(enriched: list[EnrichedOrder]) -> dict[str, float]:
    matrix = note_term_matrix(enriched)
    weights = {
        "priority": 1.4,
        "migration": 1.2,
        "compliance": 1.3,
        "discount": 0.7,
        "support": 0.9,
        "renewal": 1.1,
    }
    scores: dict[str, float] = {}
    for segment, counts in matrix.items():
        total = 0.0
        for term, count in counts.items():
            total += count * weights.get(term, 1.0)
        scores[segment] = total
    return scores
