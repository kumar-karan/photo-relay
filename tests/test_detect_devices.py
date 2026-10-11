#!/usr/bin/env python3
"""Regression tests for device detection.

Run with: python3 tests/test_detect_devices.py
"""

import os
import subprocess
import sys
import unittest
from pathlib import Path

ENGINE = Path(__file__).resolve().parent.parent / "sync_engine"
sys.path.insert(0, str(ENGINE))

import detect_devices  # noqa: E402


class TestPymobiledevice3Resolution(unittest.TestCase):
    def test_resolves_without_homebrew_on_path(self):
        """A .app launched from Finder has a minimal PATH.

        Regression: detection called "pymobiledevice3" bare, so a connected
        iPhone reported as missing whenever Homebrew was absent from PATH.
        """
        command = detect_devices.pymobiledevice3_command()
        self.assertTrue(command, "must resolve a pymobiledevice3 entry point")
        if command[0] not in ("/usr/bin/python3", sys.executable):
            self.assertTrue(
                Path(command[0]).exists(),
                f"resolved binary does not exist: {command[0]}",
            )

    def test_falls_back_to_absolute_homebrew_paths(self):
        """Resolution must not depend on PATH order or contents."""
        original = detect_devices.shutil.which
        try:
            detect_devices.shutil.which = lambda name: None
            command = detect_devices.pymobiledevice3_command()
        finally:
            detect_devices.shutil.which = original

        self.assertTrue(command)
        # Either a known absolute location, or the module under this interpreter.
        if len(command) == 1:
            self.assertTrue(Path(command[0]).exists(), f"missing binary: {command[0]}")
        else:
            self.assertIn("-m", command)
            self.assertEqual(command[-1], "pymobiledevice3")

    def test_configured_path_wins(self):
        original_config = detect_devices.CONFIG_PATH
        original_loader = detect_devices.load_config
        try:
            detect_devices.load_config = lambda: {"pymobiledevice3_bin": "/custom/pmd3"}
            command = detect_devices.pymobiledevice3_command()
            # A configured path that does not exist must be ignored, not used.
            self.assertNotEqual(command, ["/custom/pmd3"])
        finally:
            detect_devices.load_config = original_loader
            detect_devices.CONFIG_PATH = original_config

    def test_missing_config_does_not_crash(self):
        """A fresh clone ships config.example.json only."""
        original_path = detect_devices.CONFIG_PATH
        try:
            detect_devices.CONFIG_PATH = Path("/nonexistent/config.json")
            self.assertEqual(detect_devices.load_config(), {})
        finally:
            detect_devices.CONFIG_PATH = original_path


class TestConnectionLabel(unittest.TestCase):
    def test_labels_usb_and_wifi(self):
        usb = [{"name": "Karan's iPhone", "connection": "USB"}]
        wifi = [{"name": "Karan's iPhone", "connection": "Network"}]
        self.assertEqual(detect_devices.iphone_connection_label(usb), "Karan's iPhone (USB)")
        self.assertEqual(detect_devices.iphone_connection_label(wifi), "Karan's iPhone (Wi-Fi)")
        self.assertEqual(detect_devices.iphone_connection_label([]), "")

    def test_probe_runs_once_per_check(self):
        """list_iphone_devices is the slow call; check must not repeat it."""
        calls = []
        original = detect_devices.list_iphone_devices
        try:
            detect_devices.list_iphone_devices = lambda: (calls.append(1), [])[1]
            detect_devices.check_iphone_connected([])
            detect_devices.iphone_connection_label([])
        finally:
            detect_devices.list_iphone_devices = original
        self.assertEqual(calls, [])


class TestScriptRunsUnderMinimalPath(unittest.TestCase):
    def test_detector_runs_with_stripped_path(self):
        """End-to-end: the detector must not need Homebrew on PATH."""
        env = {"PATH": "/usr/bin:/bin", "HOME": os.environ.get("HOME", "")}
        result = subprocess.run(
            [sys.executable, str(ENGINE / "detect_devices.py")],
            capture_output=True,
            text=True,
            timeout=60,
            env=env,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("iPhone", result.stdout)
        self.assertIn("Detected Mode", result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
