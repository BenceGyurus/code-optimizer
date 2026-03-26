from typing import Dict, List, Tuple


def render_table(rows: List[Tuple[str, float]]) -> List[str]:
    lines = []
    for name, value in rows:
        lines.append(f"{name:20} | {value:10.2f}")
    return lines


def summarize_totals(totals: Dict[str, float]) -> Dict[str, float]:
    summary = {}
    for key, value in totals.items():
        summary[key] = float(value)
    return summary


def build_summary_report(totals: Dict[str, float], top_n: int) -> List[str]:
    ranked = sorted(totals.items(), key=lambda item: item[1], reverse=True)
    top = ranked[:top_n]
    lines = render_table(top)
    return ["REGION SUMMARY"] + lines


def group_by_prefix(items: List[str], prefix: str) -> List[str]:
    grouped = []
    for item in items:
        if item.startswith(prefix):
            grouped.append(item)
    return grouped


def dedupe_lines(lines: List[str]) -> List[str]:
    unique = []
    for line in lines:
        if line not in unique:
            unique.append(line)
    return unique


def expand_tags(tags: List[str]) -> List[str]:
    expanded = []
    for tag in tags:
        expanded.append(tag)
        expanded.append(tag.strip().lower())
    return expanded
