#!/usr/bin/env python3
"""Filesystem and template-contract checks for all native command adapters."""

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from command_aliases import HOSTS, RECEIPT, command_catalog, render, roots_for

ROOT = Path(__file__).resolve().parent.parent


class CommandAliasesTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="engineer-alias-tests-")
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name) / "home with spaces"

    def run_install(self, *args, success=True, cwd=None):
        result = subprocess.run(["bash", str(ROOT / "scripts/install-commands.sh"),
                                 "--home", str(self.home), *args],
                                capture_output=True, text=True, cwd=cwd)
        self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)
        return result

    def test_all_commands_all_formats_and_idempotence(self):
        self.run_install("--hosts", "all")
        names = set(command_catalog(ROOT))
        for host, root in roots_for(self.home).items():
            receipt = json.loads((root / RECEIPT).read_text())
            self.assertEqual(set(receipt["commands"]), names)
            expected = names - {"engineer"} if host == "hermes" else names
            self.assertEqual(len(receipt["files"]), len(expected))
            for name in expected:
                relative = name + ("/SKILL.md" if host == "hermes" else ".toml" if host == "gemini" else ".md")
                content = (root / relative).read_text()
                self.assertIn(str(ROOT / "commands" / (name + ".md")), content)
                self.assertIn(str(ROOT / "SKILL.md"), content)
                self.assertNotIn("!{", content)
                self.assertNotIn("!`", content)
                if host in ("codex", "claude", "grok", "opencode"):
                    self.assertEqual(re.findall(r"\$[A-Z][A-Z_]*", content), ["$ARGUMENTS"])
                if host == "gemini":
                    # Each TOML value is rendered as one JSON-compatible basic string.
                    fields = dict(line.split(" = ", 1) for line in content.splitlines())
                    prompt = json.loads(fields["prompt"])
                    self.assertEqual(prompt.count("{{args}}"), 1)
                if host == "hermes":
                    self.assertIn(f"name: {name}\n", content)
            if host == "hermes":
                self.assertEqual((root / "engineer").resolve(), ROOT)
        before = {str(p): p.lstat().st_mtime_ns for p in self.home.rglob("*")}
        self.run_install("--hosts", "all")
        self.run_install("--hosts", "all", "--check")
        self.assertEqual(before, {str(p): p.lstat().st_mtime_ns for p in self.home.rglob("*")})

    def test_preview_and_check_do_not_write(self):
        self.run_install("--hosts", "all", "--dry-run")
        self.run_install("--hosts", "all", "--check", success=False)
        self.run_install("--hosts", "codex,unknown", success=False)
        self.assertFalse(self.home.exists())

    def test_existing_user_command_blocks_all_hosts(self):
        path = self.home / ".grok/commands/engineer-audit.md"
        path.parent.mkdir(parents=True)
        path.write_text("my custom audit")
        self.run_install("--hosts", "codex,grok", success=False)
        self.assertEqual(path.read_text(), "my custom audit")
        self.assertFalse((self.home / ".codex").exists())

    def test_modified_managed_command_is_preserved(self):
        self.run_install("--hosts", "claude")
        path = self.home / ".claude/commands/engineer-audit.md"
        path.write_text(path.read_text() + "Local customization\n")
        self.run_install("--hosts", "claude", success=False)
        self.assertTrue(path.read_text().endswith("Local customization\n"))

    def test_migrates_original_symlink_without_editing_source(self):
        path = self.home / ".cursor/commands/engineer-audit.md"
        path.parent.mkdir(parents=True)
        source = ROOT / "commands/engineer-audit.md"
        before = source.read_bytes()
        path.symlink_to(source)
        self.run_install("--hosts", "cursor")
        self.assertFalse(path.is_symlink())
        self.assertEqual(source.read_bytes(), before)
        self.assertIn(str(source), path.read_text())

    def test_wrong_and_dangling_symlinks_are_preserved(self):
        path = self.home / ".cursor/commands/engineer-audit.md"
        path.parent.mkdir(parents=True)
        path.symlink_to(self.home / "absent")
        self.run_install("--hosts", "cursor", success=False)
        self.assertEqual(path.readlink(), self.home / "absent")

    def test_hermes_alias_directory_symlink_is_not_followed(self):
        path = self.home / ".hermes/skills/engineer-audit"
        path.parent.mkdir(parents=True)
        path.symlink_to(ROOT)
        self.run_install("--hosts", "hermes", success=False)
        self.assertEqual(path.resolve(), ROOT)

    def test_project_scope_requires_explicit_hosts(self):
        project = Path(self.temp.name) / "project"
        project.mkdir()
        self.run_install("--project", cwd=project, success=False)
        self.assertEqual(list(project.iterdir()), [])
        self.run_install("--project", "--hosts", "codex", cwd=project, success=False)
        self.assertEqual(list(project.iterdir()), [])
        self.run_install("--project", "--hosts", "claude,gemini", cwd=project)
        self.assertTrue((project / ".claude/commands/engineer-audit.md").is_file())
        self.assertTrue((project / ".gemini/commands/engineer-audit.toml").is_file())

    def test_obsolete_alias_cleanup_and_edited_stale_preflight(self):
        self.run_install("--hosts", "all")
        for host, root in roots_for(self.home).items():
            receipt_path = root / RECEIPT
            receipt = json.loads(receipt_path.read_text())
            original = next(iter(receipt["files"]))
            stale = original.replace(original.split("/")[0].split(".")[0], "engineer-retired")
            path = root / stale
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes((root / original).read_bytes())
            receipt["files"][stale] = receipt["files"][original]
            receipt_path.write_text(json.dumps(receipt))
        edited = self.home / ".grok/commands/engineer-retired.md"
        original = edited.read_bytes()
        edited.write_text("keep my edit")
        self.run_install("--hosts", "all", success=False)
        self.assertTrue((self.home / ".codex/prompts/engineer-retired.md").exists())
        self.assertEqual(edited.read_text(), "keep my edit")
        edited.write_bytes(original)
        self.run_install("--hosts", "all", "--check", success=False)
        self.run_install("--hosts", "all")
        self.assertFalse(list(self.home.rglob("engineer-retired*")))
        self.run_install("--hosts", "all", "--check")

    def test_uninstall_ownership_preview_and_idempotency(self):
        self.run_install("--hosts", "all")
        unrelated = self.home / ".hermes/skills/engineer-audit/notes.txt"
        unrelated.write_text("keep")
        self.run_install("--hosts", "all", "--uninstall", "--dry-run")
        self.run_install("--hosts", "all", "--uninstall", "--check", success=False)
        self.assertTrue((self.home / ".codex/prompts/engineer-audit.md").exists())
        self.run_install("--hosts", "all", "--uninstall")
        self.run_install("--hosts", "all", "--uninstall", "--check")
        self.run_install("--hosts", "all", "--uninstall")
        self.assertEqual(unrelated.read_text(), "keep")
        self.assertTrue((self.home / ".hermes/skills/engineer").is_symlink())
        self.assertFalse(list(self.home.rglob(RECEIPT)))

    def test_uninstall_preserves_customized_aliases_and_all_other_hosts(self):
        self.run_install("--hosts", "all")
        edited = self.home / ".grok/commands/engineer-audit.md"
        edited.write_text("custom")
        self.run_install("--hosts", "all", "--uninstall", success=False)
        self.assertEqual(edited.read_text(), "custom")
        self.assertTrue((self.home / ".codex/prompts/engineer-audit.md").exists())

    def test_receipt_paths_and_symlinks_cannot_authorize_deletion(self):
        self.run_install("--hosts", "hermes")
        root = roots_for(self.home)["hermes"]
        receipt_path = root / RECEIPT
        original = receipt_path.read_text()
        for relative in ("../../victim", "/tmp/victim", "engineer/SKILL.md", "engineer-audit/../SKILL.md"):
            receipt = json.loads(original)
            receipt["files"][relative] = "a" * 64
            receipt_path.write_text(json.dumps(receipt))
            self.run_install("--hosts", "hermes", "--uninstall", success=False)
            self.assertTrue((root / "engineer-audit/SKILL.md").exists())
        receipt_path.write_text(original)
        alias = root / "engineer-audit/SKILL.md"
        alias.unlink()
        alias.symlink_to(ROOT / "SKILL.md")
        self.run_install("--hosts", "hermes", "--uninstall", success=False)
        self.assertTrue(alias.is_symlink())

    def test_profile_roots_and_codex_literal_dollars(self):
        with patch.dict(os.environ, {"CODEX_HOME": "/tmp/codex-alias-profile", "HERMES_HOME": "/tmp/hermes-alias-profile"}):
            self.assertEqual(roots_for()["codex"], Path("/tmp/codex-alias-profile/prompts"))
            self.assertEqual(roots_for()["hermes"], Path("/tmp/hermes-alias-profile/skills"))
            self.assertEqual(roots_for(self.home)["codex"], self.home / ".codex/prompts")
        body = render("codex", "engineer-plan", "Plan", Path("/tmp/$EXAMPLE/engineer")).decode()
        self.assertIn("$$EXAMPLE", body)
        self.assertIn("Task: $ARGUMENTS", body)


if __name__ == "__main__":
    unittest.main()
