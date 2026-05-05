from pathlib import Path

from optimizer.llm.source_context import SourceContextBuilder
from optimizer.orchestrator.state_machine import State


SOURCE = '''
import math

CONSTANT = 3

def cheap(values):
    return sum(values)

def helper(value):
    return value * CONSTANT

def expensive(items):
    total = 0
    for row in items:
        for value in row:
            total += helper(value)
    return total

def branchy(items):
    total = 0
    for value in items:
        if value % 2:
            total += value
        elif value % 3:
            total -= value
        else:
            total += 1
    return total
'''.strip()


def test_source_context_uses_outline_and_candidate_previews(tmp_path: Path) -> None:
    source_path = tmp_path / "sample.py"
    source_path.write_text(SOURCE, encoding="utf-8")

    context = SourceContextBuilder(str(source_path), display_path="sample.py", max_chars=6000).render(
        State.PROFILE_READY,
        target=None,
    )

    assert "Source context mode: compact AST outline plus focused excerpts." in context
    assert "Patch path: sample.py" in context
    assert "Top optimization candidates:" in context
    assert "expensive lines" in context
    assert "Candidate preview:" in context
    assert "Focused exact source for patching" not in context


def test_source_context_focuses_exact_target_for_patch_state(tmp_path: Path) -> None:
    source_path = tmp_path / "sample.py"
    source_path.write_text(SOURCE, encoding="utf-8")

    context = SourceContextBuilder(str(source_path), display_path="sample.py", max_chars=6000).render(
        State.ANALYSIS_READY,
        target="expensive",
    )

    assert "Focused exact source for patching" in context
    assert "Symbol: expensive" in context
    assert "def expensive(items):" in context
    assert "total += helper(value)" in context
    assert "Related exact source" in context
    assert "def helper(value):" in context


def test_source_context_respects_prompt_budget(tmp_path: Path) -> None:
    source_path = tmp_path / "large.py"
    source_path.write_text(SOURCE + "\n" + "\n".join(f"VALUE_{index} = {index}" for index in range(300)), encoding="utf-8")

    context = SourceContextBuilder(str(source_path), display_path="large.py", max_chars=900).render(
        State.PROFILE_READY,
        target=None,
    )

    assert len(context) <= 900 + len("\n\n# Source context truncated to fit prompt budget.")


def test_source_context_downranks_final_aggregation_targets(tmp_path: Path) -> None:
    source_path = tmp_path / "sample.py"
    source_path.write_text(
        SOURCE
        + """

def checksum(items):
    total = 0
    for row in items:
        for value in row:
            total += value
    return total
""",
        encoding="utf-8",
    )

    context = SourceContextBuilder(str(source_path), display_path="sample.py", max_chars=6000).render(
        State.PROFILE_READY,
        target=None,
    )

    top_section = context.split("Top optimization candidates:", 1)[1].split("Use exact excerpt", 1)[0]
    assert "final_aggregation" in context
    assert not top_section.strip().startswith("1. checksum")
