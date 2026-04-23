import difflib
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DeterministicRecipe:
    target: str
    strategy: str
    rationale: str
    pattern: str
    replacement: str
    optimized_marker: str


@dataclass(frozen=True)
class DeterministicChange:
    target: str
    strategy: str
    rationale: str
    patch: str
    file_path: str
    updated_source: str
    changed: bool


_RECIPES = {
    "matrix_multiply": DeterministicRecipe(
        target="matrix_multiply",
        strategy="reorder loops to i-k-j and hoist row lookups for better locality",
        rationale="The i-k-j loop order walks each row of b contiguously and reduces Python indexing overhead.",
        pattern=r"^def matrix_multiply\(a, b\):\n.*?(?=^def |\Z)",
        replacement="""def matrix_multiply(a, b):
    \"\"\"Cache-friendlier O(n^3) matrix multiplication.

    Optimization difficulty: medium. This keeps O(n^3), but reorders the
    loops and hoists row lookups to reduce Python overhead and improve
    locality.
    \"\"\"
    rows_a = len(a)
    cols_a = len(a[0])
    rows_b = len(b)
    cols_b = len(b[0])

    if cols_a != rows_b:
        raise ValueError("Incompatible dimensions")

    result = [[0.0 for _ in range(cols_b)] for _ in range(rows_a)]
    for i in range(rows_a):
        row_a = a[i]
        row_result = result[i]
        for k in range(cols_a):
            a_ik = row_a[k]
            row_b = b[k]
            for j in range(cols_b):
                row_result[j] += a_ik * row_b[j]
    return result

""",
        optimized_marker="row_result[j] += a_ik * row_b[j]",
    ),
    "moving_average_slow": DeterministicRecipe(
        target="moving_average_slow",
        strategy="replace repeated window rescans with a sliding sum",
        rationale="A running window sum preserves results while reducing repeated overlap work from O(n * window) to O(n).",
        pattern=r"^def moving_average_slow\(values, window\):\n.*?(?=^def |\Z)",
        replacement="""def moving_average_slow(values, window):
    \"\"\"Recomputes every window sum from scratch.

    Optimization difficulty: easy. This can be replaced by a sliding-window
    running sum without changing results.
    \"\"\"
    if window <= 0:
        raise ValueError("window must be positive")
    if window > len(values):
        return []

    window_sum = sum(values[:window])
    averages = [window_sum / window]
    for index in range(window, len(values)):
        window_sum += values[index]
        window_sum -= values[index - window]
        averages.append(window_sum / window)
    return averages

""",
        optimized_marker="window_sum = sum(values[:window])",
    ),
    "join_events_to_users_slow": DeterministicRecipe(
        target="join_events_to_users_slow",
        strategy="build a user-id map once before the event loop",
        rationale="A precomputed user lookup removes repeated linear scans of the same user list.",
        pattern=r"^def join_events_to_users_slow\(events, users\):\n.*?(?=^def |\Z)",
        replacement="""def join_events_to_users_slow(events, users):
    \"\"\"Repeated linear lookup for each event.

    Optimization difficulty: easy-medium. Building a user_id -> user_name map
    avoids repeatedly scanning the same user list.
    \"\"\"
    user_names = {user["id"]: user["name"] for user in users}
    joined = []
    for event in events:
        joined.append(
            {
                "event_id": event["event_id"],
                "user_id": event["user_id"],
                "user_name": user_names.get(event["user_id"], "unknown"),
                "amount": event["amount"],
                "category": event["category"],
            }
        )
    return joined

""",
        optimized_marker='user_names = {user["id"]: user["name"] for user in users}',
    ),
    "category_totals_slow": DeterministicRecipe(
        target="category_totals_slow",
        strategy="aggregate totals in one pass while preserving category order",
        rationale="A single pass over records avoids rescanning the full record list for every category.",
        pattern=r"^def category_totals_slow\(records, categories\):\n.*?(?=^def |\Z)",
        replacement="""def category_totals_slow(records, categories):
    \"\"\"Nested category scan that can be replaced by one-pass aggregation.

    Optimization difficulty: medium. The output order must stay the same as
    the category list, but each record should only need to be visited once.
    \"\"\"
    totals = {category: {"total": 0, "count": 0} for category in categories}
    for record in records:
        category = record["category"]
        bucket = totals.get(category)
        if bucket is None:
            continue
        bucket["total"] += record["amount"]
        bucket["count"] += 1
    return totals

""",
        optimized_marker='totals = {category: {"total": 0, "count": 0} for category in categories}',
    ),
}

_GENERIC_TARGET_PRIORITY = (
    "matrix_multiply",
    "join_events_to_users_slow",
    "category_totals_slow",
    "moving_average_slow",
)


def supported_targets() -> tuple[str, ...]:
    return tuple(_RECIPES.keys())


def preferred_targets_for_project(project_path: str) -> tuple[str, ...]:
    source = _load_source(project_path)
    ordered_targets = [target for target in _GENERIC_TARGET_PRIORITY if target in source]
    ordered_targets.extend(target for target in supported_targets() if target not in ordered_targets)
    return tuple(ordered_targets)


def infer_target_from_text(text: str) -> Optional[str]:
    lowered = text or ""
    for target in _RECIPES:
        if target in lowered:
            return target
    return None


def build_change_for_target(project_path: str, target: str) -> Optional[DeterministicChange]:
    recipe = _RECIPES.get(target)
    if recipe is None:
        return None

    file_path = _resolve_file_path(project_path)
    if file_path is None or not os.path.exists(file_path):
        return None

    with open(file_path, "r", encoding="utf-8") as handle:
        source = handle.read()

    if recipe.optimized_marker in source:
        relative_path = _relative_patch_path(file_path)
        return DeterministicChange(
            target=recipe.target,
            strategy=recipe.strategy,
            rationale=recipe.rationale,
            patch=_build_patch(source, source, relative_path),
            file_path=file_path,
            updated_source=source,
            changed=False,
        )

    updated_source, replacements = re.subn(
        recipe.pattern,
        recipe.replacement,
        source,
        count=1,
        flags=re.MULTILINE | re.DOTALL,
    )
    if replacements != 1:
        return None

    relative_path = _relative_patch_path(file_path)
    return DeterministicChange(
        target=recipe.target,
        strategy=recipe.strategy,
        rationale=recipe.rationale,
        patch=_build_patch(source, updated_source, relative_path),
        file_path=file_path,
        updated_source=updated_source,
        changed=source != updated_source,
    )


def apply_change_for_target(project_path: str, target: str) -> Optional[DeterministicChange]:
    change = build_change_for_target(project_path, target)
    if change is None or not change.changed:
        return change

    with open(change.file_path, "w", encoding="utf-8") as handle:
        handle.write(change.updated_source)
    return change


def _resolve_file_path(project_path: str) -> Optional[str]:
    if os.path.isfile(project_path):
        return project_path
    if not os.path.isdir(project_path):
        return None

    top_level = [
        os.path.join(project_path, name)
        for name in sorted(os.listdir(project_path))
        if name.endswith(".py") and os.path.isfile(os.path.join(project_path, name))
    ]
    if top_level:
        return top_level[0]

    for root, dirs, files in os.walk(project_path):
        dirs[:] = sorted(dir_name for dir_name in dirs if not dir_name.startswith("."))
        for file_name in sorted(files):
            if file_name.endswith(".py"):
                return os.path.join(root, file_name)
    return None


def _load_source(project_path: str) -> str:
    file_path = _resolve_file_path(project_path)
    if file_path is None or not os.path.exists(file_path):
        return ""
    with open(file_path, "r", encoding="utf-8") as handle:
        return handle.read()


def _relative_patch_path(file_path: str) -> str:
    repo_root = _git_root(file_path)
    if repo_root:
        return os.path.relpath(file_path, repo_root)
    return os.path.basename(file_path)


def _git_root(path: str) -> Optional[str]:
    cwd = path if os.path.isdir(path) else os.path.dirname(os.path.abspath(path))
    process = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        text=True,
        capture_output=True,
        cwd=cwd or ".",
        check=False,
    )
    if process.returncode == 0:
        return process.stdout.strip()
    return None


def _build_patch(original: str, updated: str, relative_path: str) -> str:
    diff_body = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=f"a/{relative_path}",
            tofile=f"b/{relative_path}",
        )
    )
    if not diff_body:
        return ""
    return f"diff --git a/{relative_path} b/{relative_path}\n{diff_body}"
