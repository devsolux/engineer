#!/usr/bin/env python3
"""Exercise an exported installer package from outside its checkout, without LLMs."""

from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from skill_hosts import HOST_PATHS

ROOT = Path(__file__).resolve().parent.parent


class CleanInstallTests(unittest.TestCase):
    def test_export_relocation_and_complete_lifecycle(self):
        with tempfile.TemporaryDirectory(prefix="engineer-clean-install-") as temporary:
            base = Path(temporary)
            source = base / "export with spaces"
            source.mkdir()
            shutil.copy2(ROOT / "SKILL.md", source / "SKILL.md")
            shutil.copytree(ROOT / "commands", source / "commands")
            scripts = source / "scripts"
            scripts.mkdir()
            for name in ("install-all-agents.sh", "install-native-skills.py", "skill_hosts.py",
                         "install-commands.sh", "install-command-aliases.py", "command_aliases.py"):
                shutil.copy2(ROOT / "scripts" / name, scripts / name)
            home = base / "isolated home"
            project = base / "consumer project"
            project.mkdir()

            def run(installer, *args, success=True):
                result = subprocess.run(
                    [sys.executable, str(source / "scripts" / installer), "--home", str(home),
                     "--hosts", "all", *args], cwd=project, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode == 0, success, result.stdout + result.stderr)

            run("install-native-skills.py")
            run("install-command-aliases.py")
            run("install-command-aliases.py", "--check")
            old = source
            source = base / "relocated export"
            old.rename(source)
            # Managed wrappers refresh to the new path. Native links require an
            # explicit repair; the installer must not overwrite dangling links.
            run("install-native-skills.py", success=False)
            (home / ".hermes/skills/engineer").unlink()
            run("install-command-aliases.py")
            run("install-command-aliases.py", "--check")
            alias = home / ".codex/prompts/engineer-audit.md"
            self.assertIn(str(source.resolve()), alias.read_text())
            self.assertNotIn(str(old), alias.read_text())
            # Python 3.10 globbing omits dangling directory links; use known host paths.
            for relative in set(HOST_PATHS.values()):
                link = home / relative
                if link.is_symlink() and link.readlink() == old.resolve():
                    link.unlink()
            run("install-native-skills.py")
            run("install-command-aliases.py", "--uninstall")
            run("install-native-skills.py", "--uninstall")
            run("install-command-aliases.py", "--uninstall", "--check")
            self.assertEqual(list(project.iterdir()), [])
            self.assertFalse(list(home.rglob("engineer*.md")))
            self.assertFalse(list(home.rglob("engineer*.toml")))
            self.assertFalse(any((home / relative).is_symlink() for relative in HOST_PATHS.values()))


if __name__ == "__main__":
    unittest.main()
