"""Focused Stage 4 colony lifecycle contracts; deterministic source evidence."""

from __future__ import annotations

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
MOD = ROOT / "mod" / "AGOT_Alternate_World_Compatch"


def definition(relative: str, name: str) -> str:
    text = (MOD / relative).read_text(encoding="utf-8-sig")
    text = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
    match = re.search(rf"(?m)^\s*{re.escape(name)}\s*=\s*\{{", text)
    if not match:
        raise AssertionError(f"missing definition {relative}:{name}")
    opening = text.find("{", match.start(), match.end())
    depth = 0
    for index in range(opening, len(text)):
        depth += text[index] == "{"
        depth -= text[index] == "}"
        if depth == 0:
            return text[opening + 1:index]
    raise AssertionError(f"unclosed definition {relative}:{name}")


class ColonyLifecycleContracts(unittest.TestCase):
    LIFECYCLE = "common/scripted_effects/aawc_stage4_colony_lifecycle_effects.txt"

    def test_ruin_and_wilderness_are_ineligible_and_growth_is_zeroed(self):
        initialize = definition(
            "common/scripted_effects/aawc_population_effects.txt",
            "aawc_population_initialize_holding_demographics_effect",
        )
        dynamic = definition(
            "common/scripted_effects/aawc_population_effects.txt",
            "aawc_population_update_holding_dynamic_effect",
        )
        self.assertIn("aawc_reforging_cohort_clear_ineligible_settlement_effect = yes", initialize)
        self.assertIn("has_holding_type = ruin_holding", dynamic)
        self.assertIn("has_holding_type = wilderness_holding", dynamic)
        self.assertIn("aawc_population_final_growth_rate value = 0", dynamic)

    def test_blockers_remain_the_single_progressive_six_dimension_path(self):
        lifecycle = definition(self.LIFECYCLE, "aawc_stage4_refresh_colony_lifecycle_effect")
        conditions = (MOD / "common/scripted_effects/aawc_stage2_condition_effects.txt").read_text(encoding="utf-8-sig")
        self.assertIn("has_building_with_flag = obstacle", lifecycle)
        self.assertIn("aawc_stage4_colony_lifecycle_declining", lifecycle)
        self.assertIn("aawc_population_mark_holding_static_dirty_effect = yes", lifecycle)
        for dimension in ("sustenance", "habitation", "opportunity", "health", "security", "amenities"):
            self.assertIn(f"aawc_stage2_contrib_blockers_{dimension}", conditions)
        self.assertNotIn("aawc_stage2_add_contribution_effect", lifecycle)

    def test_successful_commit_enters_colony_mode_after_exact_credit(self):
        commit = definition(
            "common/scripted_effects/aawc_stage4_cohort_reservation_effects.txt",
            "aawc_stage4_expedition_commit_effect",
        )
        self.assertLess(
            commit.index("aawc_reforging_cohort_apply_transfer_packet_effect ="),
            commit.index("aawc_stage4_enter_colony_mode_effect ="),
        )

    def test_conversion_is_one_time_state_only_and_preserves_protected_surfaces(self):
        lifecycle = definition(self.LIFECYCLE, "aawc_stage4_refresh_colony_lifecycle_effect")
        self.assertIn("remove_variable = aawc_stage4_colony_mode", lifecycle)
        self.assertIn("aawc_stage4_colony_conversion_complete", lifecycle)
        for forbidden in ("set_holding_type", "change_title_holder", "get_title", "aawc_reforging_cohort_clear", "apply_transfer"):
            self.assertNotIn(forbidden, lifecycle)

    def test_stage1_stage2_boundaries_and_unresolved_balance_are_explicit(self):
        lifecycle = (MOD / self.LIFECYCLE).read_text(encoding="utf-8-sig")
        unresolved = (ROOT / "catalogue/stage4/colony_lifecycle_unresolved_config.md").read_text(encoding="utf-8")
        monthly = definition(
            "common/scripted_effects/aawc_population_effects.txt",
            "aawc_population_apply_holding_monthly_growth_effect",
        )
        self.assertIn("aawc_stage4_refresh_colony_lifecycle_effect = yes", monthly)
        self.assertNotIn("aawc_reforging_cohort_", lifecycle.replace("aawc_reforging_cohort_clear", ""))
        self.assertIn("final fully-cleared colony neutrality target", unresolved)
        self.assertIn("per-blocker resident-decline coefficients", unresolved)

    def test_changed_ck3_files_have_balanced_braces(self):
        for relative in (
            self.LIFECYCLE,
            "common/scripted_effects/aawc_stage4_cohort_reservation_effects.txt",
            "common/scripted_effects/aawc_population_effects.txt",
        ):
            text = (MOD / relative).read_text(encoding="utf-8-sig")
            stripped = "\n".join(line.split("#", 1)[0] for line in text.splitlines())
            self.assertEqual(stripped.count("{"), stripped.count("}"), relative)


if __name__ == "__main__":
    unittest.main(verbosity=2)
