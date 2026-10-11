#!/usr/bin/env python3
"""Exercise native installation in isolated homes without launching LLMs."""

import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from skill_hosts import HOST_PATHS, skill_paths

ROOT = Path(__file__).resolve().parent.parent


class NativeSkillsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="engineer-native-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home with spaces"

    def install(self, *args, success=True):
        result = subprocess.run(
            ["bash", str(ROOT / "scripts/install-all-agents.sh"), "--home", str(self.home), *args],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def test_all_hosts_and_repeat_without_global_side_effects(self):
        self.install("--hosts", "all")
        before = {str(p): p.lstat().st_mtime_ns for p in self.home.rglob("*")}
        self.install("--hosts", "all")
        self.assertEqual(before, {str(p): p.lstat().st_mtime_ns for p in self.home.rglob("*")})
        for rel in HOST_PATHS.values():
            path = self.home / rel
            self.assertEqual(path.resolve(), ROOT)
            for bundled in ("SKILL.md", "references/project-detect.md", "scripts/engineer-scan.sh"):
                self.assertEqual((path / bundled).read_bytes(), (ROOT / bundled).read_bytes())
        self.assertFalse((self.home / "AGENTS.md").exists())
        self.assertFalse((self.home / ".hermes/memories").exists())
        self.assertFalse((self.home / ".cursor/commands").exists())
        self.assertFalse((self.home / ".claude/CLAUDE.md").exists())

    def test_preview_and_bad_arguments_write_nothing(self):
        self.install("--hosts", "all", "--dry-run")
        self.assertFalse(self.home.exists())
        for args in (("--hosts", "claude,typo"), ("--hosts", ""), ("--hosts",), ("--hosts", "all", "--skills-dir", "unused")):
            self.install(*args, success=False)
            self.assertFalse(self.home.exists())

    def test_selected_host_creates_fresh_root(self):
        self.install("--hosts", "hermes")
        self.assertTrue((self.home / ".hermes/skills/engineer/SKILL.md").is_file())
        self.assertEqual([p.name for p in self.home.iterdir()], [".hermes"])

    def test_auto_only_detected_roots(self):
        (self.home / ".claude").mkdir(parents=True)
        self.install()
        self.assertTrue((self.home / ".claude/skills/engineer").is_symlink())
        self.assertEqual([p.name for p in self.home.iterdir()], [".claude"])

    def test_conflict_preflight_preserves_data_and_other_hosts(self):
        conflict = self.home / ".hermes/skills/engineer"
        conflict.mkdir(parents=True)
        (conflict / "local.txt").write_text("keep me")
        self.install("--hosts", "claude,hermes", success=False)
        self.assertEqual((conflict / "local.txt").read_text(), "keep me")
        self.assertFalse((self.home / ".claude").exists())

    def test_wrong_and_dangling_links_are_preserved(self):
        conflict = self.home / ".claude/skills/engineer"
        conflict.parent.mkdir(parents=True)
        for target in (self.home, self.home / "missing"):
            conflict.symlink_to(target)
            self.install("--hosts", "claude", success=False)
            self.assertEqual(conflict.readlink(), target)
            conflict.unlink()

    def test_uninstall_removes_only_own_links_and_skips_foreign_paths(self):
        self.install("--hosts", "all")
        foreign = self.home / ".claude/skills/engineer"
        foreign.unlink()
        foreign.mkdir()
        (foreign / "custom.txt").write_text("keep")
        moved = self.home / ".gemini/skills/engineer"
        moved.unlink()
        moved.symlink_to(self.home / "moved-checkout")
        self.install("--hosts", "all", "--uninstall", "--dry-run")
        self.assertTrue((self.home / ".cursor/skills/engineer").is_symlink())
        result = self.install("--hosts", "all", "--uninstall")
        self.assertIn("skip (not linked to this checkout)", result.stdout)
        self.assertEqual((foreign / "custom.txt").read_text(), "keep")
        self.assertEqual(moved.readlink(), self.home / "moved-checkout")
        skipped = {".claude/skills/engineer", ".gemini/skills/engineer"}
        self.assertFalse(any((self.home / rel).is_symlink() for rel in set(HOST_PATHS.values()) - skipped))
        self.install("--hosts", "all", "--uninstall")
        self.install("--hosts", "all", "--uninstall", "--pull", success=False)

    def test_installer_chain_imports_on_python_before_3_10(self):
        # Stock macOS python3 is 3.9; PEP 604 annotations must stay lazy there.
        for name in ("skill_hosts.py", "command_aliases.py", "install-native-skills.py",
                     "install-command-aliases.py", "install-host-activation.py", "engineer-doctor.py"):
            self.assertIn("from __future__ import annotations", (ROOT / "scripts" / name).read_text(), name)

    def test_custom_native_directory(self):
        custom = Path(self.temp.name) / "another host/skills"
        self.install("--skills-dir", str(custom))
        self.assertEqual((custom / "engineer").resolve(), ROOT)
        self.assertFalse(self.home.exists())

    def test_profile_roots_and_explicit_home_isolation(self):
        env = {"HERMES_HOME": str(self.home / "hermes-profile"),
               "CLAUDE_CONFIG_DIR": str(self.home / "claude-profile"),
               "XDG_CONFIG_HOME": str(self.home / "xdg")}
        with patch.dict(os.environ, env):
            paths = skill_paths()
            self.assertEqual(paths["hermes"], Path(env["HERMES_HOME"]) / "skills/engineer")
            self.assertEqual(paths["claude"], Path(env["CLAUDE_CONFIG_DIR"]) / "skills/engineer")
            self.assertEqual(paths["opencode"], Path(env["XDG_CONFIG_HOME"]) / "opencode/skills/engineer")
            self.install("--hosts", "hermes")
            self.assertFalse((self.home / "hermes-profile").exists())

    def test_doctor_accepts_native_only_and_detects_missing_selected_host(self):
        spec = importlib.util.spec_from_file_location("doctor", ROOT / "scripts/engineer-doctor.py")
        doctor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(doctor)
        self.install("--hosts", "codex,hermes")
        with patch.object(doctor, "host_inventory", return_value={"available": False, "hosts": []}):
            report = doctor.build_report(ROOT, self.home, "codex,hermes")
            self.assertEqual(report["decision"], "healthy")
            self.assertEqual(report["activation_adapters"], [])
            (self.home / ".hermes/skills/engineer").unlink()
            self.assertEqual(doctor.build_report(ROOT, self.home, "codex,hermes")["decision"], "repair_required")

    def test_doctor_flags_dangling_links_and_accepts_marketplace_copies(self):
        spec = importlib.util.spec_from_file_location("doctor", ROOT / "scripts/engineer-doctor.py")
        doctor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(doctor)
        with patch.object(doctor, "host_inventory", return_value={"available": False, "hosts": []}):
            dangling = self.home / ".claude/skills/engineer"
            dangling.parent.mkdir(parents=True)
            dangling.symlink_to(self.home / "moved-checkout")
            item = doctor.build_report(ROOT, self.home, "claude")["installations"][0]
            self.assertEqual((item["present"], item["status"]), (True, "invalid"))
            dangling.unlink()
            cache = self.home / ".claude/plugins/cache/devsolux-engineer/engineer"
            for version, text in (("1.9.0", '---\nname: engineer\nmetadata:\n  version: "0.0.0"\n---\n'),
                                  ("1.10.0", (ROOT / "SKILL.md").read_text())):
                skill = cache / version / "skills/engineer"
                skill.mkdir(parents=True)
                (skill / "SKILL.md").write_text(text)
            report = doctor.build_report(ROOT, self.home, "claude")
            self.assertEqual(report["decision"], "healthy")
            self.assertEqual(report["installations"][0]["mode"], "plugin")
            self.assertIn("1.10.0", report["installations"][0]["location"])


if __name__ == "__main__":
    unittest.main()
