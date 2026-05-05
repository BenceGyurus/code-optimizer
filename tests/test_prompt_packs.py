from pathlib import Path

from optimizer.llm.prompt_loader import PromptLoader


REPO_ROOT = Path(__file__).resolve().parents[1]
PROMPTS_DIR = REPO_ROOT / "prompts"
FULL_SCRIPT = REPO_ROOT / "scripts" / "evaluate_debian_full.sh"

EXPECTED_PACKS = {
    "agentic",
    "concise",
    "cot",
    "default",
    "few_shot",
    "hardware_focus",
    "hypothesis_driven",
    "knowledge_gen",
    "least_to_most",
    "negative_constraints",
    "one_shot",
    "prompt_chaining",
    "reasoning_goal",
    "role_create",
    "self_refine",
    "structured_tags",
    "zero_shot",
}


def _load_pack(name: str):
    loader = PromptLoader(str(PROMPTS_DIR))
    pack = loader.get_pack(name)
    assert pack is not None
    return pack


def test_all_expected_prompt_packs_are_discoverable_and_complete():
    loader = PromptLoader(str(PROMPTS_DIR))

    assert EXPECTED_PACKS.issubset(set(loader.list_packs()))
    for name in EXPECTED_PACKS:
        pack = loader.get_pack(name)
        assert pack is not None
        assert pack.validate() == []


def test_prompt_templates_do_not_embed_benchmark_file_names():
    forbidden_terms = ("heavy_compute.py", "extreme_compute.py")

    for path in PROMPTS_DIR.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".yaml"}:
            continue
        text = path.read_text(encoding="utf-8")
        for term in forbidden_terms:
            assert term not in text, f"{term} leaked into {path}"


def test_prompt_templates_do_not_use_placeholder_patch_examples():
    forbidden_fragments = ('"patch":"diff --git ..."', "patch\":\"diff --git ...")

    for path in PROMPTS_DIR.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".yaml"}:
            continue
        text = path.read_text(encoding="utf-8")
        for fragment in forbidden_fragments:
            assert fragment not in text, f"placeholder patch leaked into {path}"


def test_prompt_templates_do_not_require_diff_git_patches():
    forbidden_fragments = (
        "beginning with diff --git",
        "start with `diff --git`",
        "starts with `diff --git`",
        "diff --git patch",
        "unified diff",
        "unified-diff",
    )

    for path in PROMPTS_DIR.rglob("*"):
        if not path.is_file() or path.suffix not in {".md", ".yaml"}:
            continue
        text = path.read_text(encoding="utf-8").lower()
        for fragment in forbidden_fragments:
            assert fragment not in text, f"{fragment!r} leaked into {path}"


def test_propose_change_prompts_prefer_structured_patch_format():
    for path in PROMPTS_DIR.glob("*/propose_change.md"):
        text = path.read_text(encoding="utf-8")
        assert "*** Begin Patch" in text, f"structured patch guidance missing from {path}"


def test_strategy_markers_remain_distinct():
    default_master = _load_pack("default").get_prompt("master")
    zero_shot_master = _load_pack("zero_shot").get_prompt("master")
    few_shot_master = _load_pack("few_shot").get_prompt("master")
    one_shot_master = _load_pack("one_shot").get_prompt("master")
    prompt_chaining_master = _load_pack("prompt_chaining").get_prompt("master")
    self_refine_master = _load_pack("self_refine").get_prompt("master")
    structured_tags_master = _load_pack("structured_tags").get_prompt("master")
    hypothesis_master = _load_pack("hypothesis_driven").get_prompt("master")
    negative_constraints_master = _load_pack("negative_constraints").get_prompt("master")

    assert default_master is not None
    assert zero_shot_master is not None
    assert few_shot_master is not None
    assert one_shot_master is not None
    assert prompt_chaining_master is not None
    assert self_refine_master is not None
    assert structured_tags_master is not None
    assert hypothesis_master is not None
    assert negative_constraints_master is not None

    assert "Best Result" in default_master
    assert "Best Result" not in zero_shot_master
    assert "visible context only" in zero_shot_master.lower()
    assert "Example A" in few_shot_master
    assert "Never copy placeholder" in few_shot_master
    assert "One-Shot Demonstration" in one_shot_master
    assert "prompt-chaining" in prompt_chaining_master.lower()
    assert "at most 3 short" in _load_pack("cot").get_prompt("master")
    assert "self_check" in self_refine_master
    assert "<runtime_contract>" in structured_tags_master
    assert "hypothesis" in hypothesis_master
    assert "Hard Constraints" in negative_constraints_master


def test_full_debian_script_default_prompt_matrix_includes_new_packs():
    script_text = FULL_SCRIPT.read_text(encoding="utf-8")

    for name in EXPECTED_PACKS:
        assert name in script_text
