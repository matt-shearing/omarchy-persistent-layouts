#!/usr/bin/env python3
import importlib.machinery
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "bin" / "persistent-layouts"
loader = importlib.machinery.SourceFileLoader("persistent_layouts", str(CLI))
SPEC = importlib.util.spec_from_file_location("persistent_layouts", CLI, loader=loader)
cli = importlib.util.module_from_spec(SPEC)
loader.exec_module(cli)


class SanitizeTests(unittest.TestCase):
    def test_output_names(self):
        self.assertEqual(cli.check_output_name("eDP-2"), "eDP-2")
        self.assertEqual(cli.check_output_name("DP-5"), "DP-5")
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
        with self.assertRaises(SystemExit):
            cli.check_mode("3840x2160@60; rm -rf /")
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

    def test_match_ignores_connector(self):
        profile = {
            "outputs": [
                {"match": {"make": "BOE", "model": "NE160QDM-NZ6"}},
                {"match": {"make": "LG Electronics", "model": "LG TV SSCR2"}},
            ]
        }
        connected = [
            {"make": "BOE", "model": "NE160QDM-NZ6", "name": "eDP-2"},
            {"make": "LG Electronics", "model": "LG TV SSCR2", "name": "DP-9"},
        ]
        match = cli.detect([{"id": "remote", **profile}], connected)
        self.assertEqual(match["id"], "remote")

    def test_no_match_when_set_differs(self):
        profile = {"id": "three", "outputs": [{"match": {"make": "BOE", "model": "X"}}]}
        connected = [{"make": "BOE", "model": "X", "name": "eDP-1"}, {"make": "AOC", "model": "Y", "name": "DP-1"}]
        self.assertIsNone(cli.detect([profile], connected))


class ModelJsTests(unittest.TestCase):
    def test_plugin_dir_helper_shape(self):
        text = (ROOT / "Model.js").read_text()
        self.assertIn("function pluginDirFromUrl", text)
        self.assertIn("function parseStatus", text)


if __name__ == "__main__":
    unittest.main()
