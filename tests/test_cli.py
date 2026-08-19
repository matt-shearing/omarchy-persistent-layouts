#!/usr/bin/env python3
import importlib.machinery
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "persistent-layouts"
loader = importlib.machinery.SourceFileLoader("persistent_layouts", str(CLI))
SPEC = importlib.util.spec_from_file_location("persistent_layouts", CLI, loader=loader)
cli = importlib.util.module_from_spec(SPEC)
loader.exec_module(cli)


def mon(name, make, model, w, h, x, y, scale, serial="", rr=60.0):
    return {
        "name": name,
        "make": make,
        "model": model,
        "serial": serial,
        "description": f"{make} {model} {serial}".strip(),
        "width": w,
        "height": h,
        "refreshRate": rr,
        "x": x,
        "y": y,
        "scale": scale,
    }


def spec(make, model, mode, scale, pos, label="", serial=""):
    return {
        "match": {"make": make, "model": model, "serial": serial},
        "mode": mode,
        "scale": scale,
        "position": pos,
        "label": label,
    }


class SanitizeTests(unittest.TestCase):
    def test_output_names(self):
        self.assertEqual(cli.check_output_name("eDP-2"), "eDP-2")
        self.assertEqual(cli.check_output_name("HDMI-A-1"), "HDMI-A-1")
        with self.assertRaises(SystemExit):
            cli.check_output_name('eDP-2"; os.execute("id")')
        with self.assertRaises(SystemExit):
            cli.check_output_name("../evil")

    def test_mode_and_position(self):
        self.assertEqual(cli.check_mode("3840x2160@60.00"), "3840x2160@60.00")
        self.assertEqual(cli.check_mode("preferred"), "preferred")
        self.assertEqual(cli.check_position("-420x-1350"), "-420x-1350")
        self.assertEqual(cli.check_position("auto"), "auto")
        # A mode string must never be able to carry a shell payload through.
        with self.assertRaises(SystemExit):
            cli.check_mode("3840x2160@60; " + "rm -" + "rf /")
        with self.assertRaises(SystemExit):
            cli.check_position("0x0;id")

    def test_scale(self):
        self.assertEqual(cli.check_scale(1.6), 1.6)
        with self.assertRaises(SystemExit):
            cli.check_scale(99)
        with self.assertRaises(SystemExit):
            cli.check_scale("nope")

    def test_lua_string(self):
        self.assertEqual(cli.lua_string("DP-5"), '"DP-5"')
        self.assertEqual(cli.lua_string('a"b'), '"a\\"b"')


class FingerprintTests(unittest.TestCase):
    def test_make_model(self):
        self.assertEqual(
            cli.fingerprint({"make": "BOE", "model": "NE160QDM-NZ6", "name": "eDP-2"}),
            "BOE|NE160QDM-NZ6",
        )

    def test_connector_name_is_not_identity(self):
        """Framework ports renumber, so DP-3 vs DP-9 must not change the match."""
        profile = {
            "id": "remote",
            "outputs": [
                spec("BOE", "NE160QDM-NZ6", "2560x1600@165.00", 1.25, "0x0"),
                spec("LG Electronics", "LG TV SSCR2", "3840x2160@60.00", 1.6, "-2400x0"),
            ],
        }
        connected = [
            mon("eDP-2", "BOE", "NE160QDM-NZ6", 2560, 1600, 0, 0, 1.25),
            mon("DP-9", "LG Electronics", "LG TV SSCR2", 3840, 2160, -2400, 0, 1.6),
        ]
        self.assertEqual(cli.detect([profile], connected)["id"], "remote")


class PlaceholderSerialTests(unittest.TestCase):
    def test_generic_scaler_serials_are_flagged(self):
        self.assertTrue(cli.placeholder_serial("0x01010101"))
        self.assertTrue(cli.placeholder_serial("0x00000000"))

    def test_real_serials_are_not_flagged(self):
        self.assertFalse(cli.placeholder_serial("0x00032867"))
        self.assertFalse(cli.placeholder_serial(""))


class LabelTests(unittest.TestCase):
    def test_same_model_panels_get_distinguishable_labels(self):
        """The Arzopa apes the TV's EDID. The UI must still tell them apart."""
        tv = mon("DP-5", "LG Electronics", "LG TV SSCR2", 3840, 2160, 0, 0, 1.6, "0x01010101")
        arzopa = mon("DP-3", "LG Electronics", "LG TV SSCR2", 1920, 1080, 0, 0, 1.0, "0x01010101")
        self.assertNotEqual(cli.auto_label(tv), cli.auto_label(arzopa))
        self.assertIn("3840x2160", cli.auto_label(tv))
        self.assertIn("1920x1080", cli.auto_label(arzopa))

    def test_untrustworthy_edid_is_marked(self):
        arzopa = mon("DP-3", "LG Electronics", "LG TV SSCR2", 1920, 1080, 0, 0, 1.0, "0x01010101")
        self.assertIn("unverified EDID", cli.auto_label(arzopa))


class DeskTests(unittest.TestCase):
    """The real desk: laptop + espresso eD15 + Arzopa behind a fake LG EDID."""

    laptop = mon("eDP-2", "BOE", "NE160QDM-NZ6", 2560, 1600, 0, 0, 1.25, rr=165.0)
    espresso = mon("DP-3", "ESP", "eD15(2024)", 1920, 1080, 32, -1120, 1.0, "0x00032867")
    arzopa = mon("DP-5", "LG Electronics", "LG TV SSCR2", 1920, 1080, -1920, 0, 1.0, "0x01010101")
    tv = mon("DP-5", "LG Electronics", "LG TV SSCR2", 3840, 2160, -420, -1350, 1.6, "0x01010101")

    two = {
        "id": "remote-2-screen-4k",
        "outputs": [
            spec("BOE", "NE160QDM-NZ6", "2560x1600@165.00", 1.25, "0x0"),
            spec("LG Electronics", "LG TV SSCR2", "3840x2160@60.00", 1.6, "-420x-1350", "LG 4K TV"),
        ],
    }
    three = {
        "id": "remote-3-screen",
        "outputs": [
            spec("BOE", "NE160QDM-NZ6", "2560x1600@165.00", 1.25, "0x0"),
            spec("ESP", "eD15(2024)", "1920x1080@60.00", 1.0, "32x-1120", "espresso eD15"),
            spec("LG Electronics", "LG TV SSCR2", "1920x1080@60.00", 1.0, "-1920x0", "Arzopa"),
        ],
    }

    def test_two_screen_profile_loses_when_three_are_plugged_in(self):
        mons = [self.laptop, self.espresso, self.arzopa]
        self.assertFalse(cli.profile_matches_topology(self.two, mons))
        self.assertEqual(cli.detect([self.two, self.three], mons)["id"], "remote-3-screen")

    def test_two_screen_profile_wins_at_the_tv(self):
        mons = [self.laptop, self.tv]
        self.assertEqual(cli.detect([self.two, self.three], mons)["id"], "remote-2-screen-4k")

    def test_specs_land_on_the_right_panels(self):
        mons = [self.laptop, self.espresso, self.arzopa]
        mapping = cli.assign_outputs(self.three, mons)
        by_model = {(s.get("match") or {}).get("model"): m["name"] for s, m in mapping}
        self.assertEqual(by_model["NE160QDM-NZ6"], "eDP-2")
        self.assertEqual(by_model["eD15(2024)"], "DP-3")
        self.assertEqual(by_model["LG TV SSCR2"], "DP-5")

    def test_leftover_monitor_is_never_conscripted(self):
        """A 1-output profile must not absorb an unrelated second display."""
        one = {
            "id": "laptop-only",
            "outputs": [spec("BOE", "NE160QDM-NZ6", "2560x1600@165.00", 1.25, "0x0")],
        }
        mons = [self.laptop, self.espresso]
        self.assertFalse(cli.profile_matches_topology(one, mons))
        self.assertIsNone(cli.detect([one], mons))

    def test_already_applied_is_measured_against_real_state(self):
        mons = [self.laptop, self.espresso, self.arzopa]
        self.assertTrue(cli.profile_is_applied(self.three, mons))

    def test_arzopa_at_4k_counts_as_not_applied(self):
        """The failure that blanked the panel: 4K on a 1080p sink."""
        blown = dict(self.arzopa, width=3840, height=2160, scale=1.6)
        mons = [self.laptop, self.espresso, blown]
        self.assertFalse(cli.profile_is_applied(self.three, mons))


class AmbiguityTests(unittest.TestCase):
    """The TV and the Arzopa are one identity, so a set can fit two desks."""

    laptop = mon("eDP-2", "BOE", "NE160QDM-NZ6", 2560, 1600, 0, 0, 1.25, rr=165.0)
    lgish = mon("DP-5", "LG Electronics", "LG TV SSCR2", 1920, 1080, -1920, 0, 1.0, "0x01010101")

    tv_desk = {
        "id": "tv",
        "outputs": [
            spec("BOE", "NE160QDM-NZ6", "2560x1600@165.00", 1.25, "0x0"),
            spec("LG Electronics", "LG TV SSCR2", "3840x2160@60.00", 1.6, "-420x-1350"),
        ],
    }
    portable_desk = {
        "id": "portable",
        "outputs": [
            spec("BOE", "NE160QDM-NZ6", "2560x1600@165.00", 1.25, "0x0"),
            spec("LG Electronics", "LG TV SSCR2", "1920x1080@60.00", 1.0, "-1920x0"),
        ],
    }

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        saved_choice, saved_active = cli.CHOICE_PATH, cli.ACTIVE_PATH
        cli.CHOICE_PATH = Path(self.tmp.name) / "choices.json"
        cli.ACTIVE_PATH = Path(self.tmp.name) / "active"

        def restore():
            cli.CHOICE_PATH = saved_choice
            cli.ACTIVE_PATH = saved_active

        self.addCleanup(restore)

    def test_both_profiles_are_reported_as_candidates(self):
        mons = [self.laptop, self.lgish]
        self.assertEqual(
            sorted(cli.detect_ambiguous([self.tv_desk, self.portable_desk], mons)),
            ["portable", "tv"],
        )

    def test_an_explicit_choice_is_remembered_for_that_set(self):
        mons = [self.laptop, self.lgish]
        cli.CHOICE_PATH.write_text(json.dumps({cli.topology_id(mons): "portable"}))
        self.assertEqual(cli.detect([self.tv_desk, self.portable_desk], mons)["id"], "portable")

    def test_a_choice_survives_a_mode_change_on_that_set(self):
        """Pinning is keyed to which displays are plugged in, not their modes."""
        mons = [self.laptop, self.lgish]
        cli.CHOICE_PATH.write_text(json.dumps({cli.topology_id(mons): "tv"}))
        rescaled = [self.laptop, dict(self.lgish, width=3840, height=2160, scale=1.6)]
        self.assertEqual(cli.detect([self.tv_desk, self.portable_desk], rescaled)["id"], "tv")

    def test_without_a_choice_the_applied_layout_wins(self):
        """Never overrule what is already on the glass on a bare tie."""
        mons = [self.laptop, self.lgish]
        self.assertEqual(cli.detect([self.tv_desk, self.portable_desk], mons)["id"], "portable")

    def test_topology_id_ignores_modes(self):
        a = cli.topology_id([self.laptop, self.lgish])
        b = cli.topology_id([self.laptop, dict(self.lgish, width=3840, height=2160)])
        self.assertEqual(a, b)


class ModelJsTests(unittest.TestCase):
    def test_helpers_exist(self):
        text = (ROOT / "Model.js").read_text()
        for fn in ("pluginDirFromUrl", "parseStatus", "displayLabel", "isAmbiguous"):
            self.assertIn(f"function {fn}", text)


if __name__ == "__main__":
    unittest.main()
