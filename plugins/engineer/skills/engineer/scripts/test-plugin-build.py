#!/usr/bin/env python3
"""Build, relocation, archive, identity, and overwrite regression tests; no hosts."""
from pathlib import Path
import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location('plugin_build', ROOT / 'scripts/build-plugin.py')
BUILD = importlib.util.module_from_spec(spec)
spec.loader.exec_module(BUILD)


class PluginBuildTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='engineer-build-test-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name) / 'source with spaces'
        self.root.mkdir()
        for entry in (*BUILD.INCLUDE, 'packaging', 'Makefile', '.claude-plugin', '.agents'):
            src, dst = ROOT / entry, self.root / entry
            if src.is_dir():
                shutil.copytree(src, dst, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
            else:
                shutil.copy2(src, dst)

    def test_identity_discovery_and_relocation(self):
        target = BUILD.build(self.root)
        for rel in ('plugin.json', '.claude-plugin/plugin.json', '.codex-plugin/plugin.json'):
            meta = json.loads((target / rel).read_text())
            self.assertEqual(meta['name'], 'engineer')
            self.assertEqual(meta['version'], BUILD.version(self.root))
        portable = json.loads((target / 'plugin.json').read_text())
        self.assertNotIn('skills', portable)
        self.assertTrue((target / 'skills/engineer/SKILL.md').is_file())
        wrapper = (target / 'commands/audit.md').read_text()
        self.assertIn('${CLAUDE_PLUGIN_ROOT}/skills/engineer/commands/engineer-audit.md', wrapper)
        self.assertNotIn(str(self.root), wrapper)
        self.assertEqual(len(list((target / 'commands').glob('*.md'))),
                         len(list((ROOT / 'commands').glob('engineer-*.md'))))
        self.assertFalse((target / 'mcp.json').exists())
        for catalog in ('.claude-plugin/marketplace.json', '.agents/plugins/marketplace.json'):
            self.assertEqual(json.loads((self.root / catalog).read_text())['name'], 'devsolux-engineer')
        renamed = self.root.with_name('relocated source')
        self.root.rename(renamed)
        BUILD.build(renamed, check=True)
        result = subprocess.run(['bash', str(renamed / 'plugins/engineer/skills/engineer/scripts/engineer-scan.sh'), '--help'], capture_output=True)
        self.assertEqual(result.returncode, 0)

    def test_reproducible_archive_and_exclusions(self):
        (self.root / 'templates/.env').write_text('PRIVATE_FIXTURE_ONLY=not-a-real-secret\n')
        target = BUILD.build(self.root)
        one = BUILD.package(self.root, target).read_bytes()
        self.assertEqual(one, BUILD.package(self.root, BUILD.build(self.root)).read_bytes())
        BUILD.build(self.root, check=True)
        with zipfile.ZipFile(BUILD.package(self.root, target)) as archive:
            names = archive.namelist()
            self.assertEqual(names, sorted(names))
            self.assertIn('plugin.json', names)
            self.assertIn('skills/engineer/SKILL.md', names)
            self.assertFalse(any('.env' in Path(n).parts or '__pycache__' in n or n.startswith(('research/', 'evals/')) for n in names))
            self.assertEqual(archive.getinfo('skills/engineer/scripts/engineer-scan.sh').external_attr >> 16 & 0o777, 0o755)

    def test_command_wrappers_reuse_canonical_descriptions(self):
        target = BUILD.build(self.root)
        for source in sorted((self.root / 'commands').glob('engineer-*.md')):
            wrapper = (target / 'commands' / (source.stem.removeprefix('engineer-') + '.md')).read_text()
            description = json.loads(wrapper.split('\n')[1].removeprefix('description: '))
            self.assertEqual(description, BUILD.command_description(source))
            self.assertNotIn('workflow"', wrapper.split('\n')[1])
        path = self.root / 'commands/engineer-audit.md'
        path.write_text('# /engineer-audit\n\nNo frontmatter.\n')
        with self.assertRaisesRegex(ValueError, 'description'):
            BUILD.render(self.root)

    def test_desktop_metadata_never_blocks_or_ships(self):
        target = BUILD.build(self.root)
        for rel in ('.DS_Store', 'skills/engineer/.DS_Store', 'commands/._audit.md'):
            (target / rel).write_bytes(b'\0metadata')
        BUILD.build(self.root, check=True)
        with zipfile.ZipFile(BUILD.package(self.root, target)) as archive:
            self.assertFalse(any(Path(n).name in {'.DS_Store', '._audit.md'} for n in archive.namelist()))
        BUILD.build(self.root)
        self.assertFalse((target / '.DS_Store').exists())
        (self.root / 'references/.DS_Store').write_bytes(b'\0metadata')
        self.assertNotIn('skills/engineer/references/.DS_Store', BUILD.render(self.root))

    def test_checkout_umask_is_not_drift(self):
        target = BUILD.build(self.root)
        for rel in ('README.md', 'skills/engineer/scripts/engineer-scan.sh'):
            path = target / rel
            path.chmod(path.stat().st_mode | 0o020)
        BUILD.build(self.root, check=True)
        BUILD.build(self.root)
        (target / 'skills/engineer/scripts/engineer-scan.sh').chmod(0o644)
        with self.assertRaisesRegex(ValueError, 'drift'):
            BUILD.build(self.root, check=True)

    def test_modified_generated_file_is_preserved(self):
        target = BUILD.build(self.root)
        path = target / 'README.md'
        path.write_text('user edit\n')
        with self.assertRaisesRegex(ValueError, 'modified'):
            BUILD.build(self.root)
        self.assertEqual(path.read_text(), 'user edit\n')

    def test_unowned_directory_is_preserved(self):
        target = self.root / 'plugins/engineer'
        target.mkdir(parents=True)
        path = target / 'mine.txt'
        path.write_text('preserve')
        with self.assertRaisesRegex(ValueError, 'unowned'):
            BUILD.build(self.root)
        self.assertEqual(path.read_text(), 'preserve')

    def test_unexpected_file_and_symlink_are_rejected(self):
        target = BUILD.build(self.root)
        (target / 'unexpected').write_text('do not delete')
        with self.assertRaisesRegex(ValueError, 'unexpected'):
            BUILD.build(self.root)
        (self.root / 'templates/link').symlink_to(ROOT / 'SKILL.md')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            BUILD.render(self.root)

    def test_source_change_requires_rebuild(self):
        BUILD.build(self.root)
        path = self.root / 'commands/engineer-audit.md'
        path.write_text(path.read_text() + '\nReviewed source edit.\n')
        with self.assertRaisesRegex(ValueError, r'drift \(changed: .*skills/engineer/commands/engineer-audit\.md'):
            BUILD.build(self.root, check=True)
        BUILD.build(self.root)
        BUILD.build(self.root, check=True)
        (self.root / 'assets/new-icon.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg"/>\n')
        with self.assertRaisesRegex(ValueError, r'drift \(missing: skills/engineer/assets/new-icon\.svg; changed: \.engineer-build\.json\)'):
            BUILD.build(self.root, check=True)

    def test_clean_preserves_source_and_session_state(self):
        for rel in ('.engineer/receipt.json', '.venv/keep', '.build/tests/log', 'dist/archive'):
            path = self.root / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('preserve unless disposable')
        result = subprocess.run([sys.executable, str(self.root / 'scripts/clean-build.py')], capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        for rel in ('.engineer/receipt.json', '.venv/keep', 'SKILL.md'):
            self.assertTrue((self.root / rel).is_file())
        self.assertFalse((self.root / '.build').exists())
        self.assertFalse((self.root / 'dist').exists())
        outside = Path(self.tmp.name) / 'outside'
        outside.mkdir()
        (outside / 'keep').write_text('preserve')
        (self.root / 'dist').symlink_to(outside, target_is_directory=True)
        result = subprocess.run([sys.executable, str(self.root / 'scripts/clean-build.py')], capture_output=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((outside / 'keep').read_text(), 'preserve')

    def test_make_install_identifiers_without_installing(self):
        result = subprocess.run(['make', '-n', 'install-claude', 'install-codex', 'PYTHON=' + sys.executable], cwd=self.root, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('claude plugin install engineer@devsolux-engineer', result.stdout)
        self.assertIn('codex plugin add engineer@devsolux-engineer', result.stdout)
        self.assertNotIn('devsolux@engineer', result.stdout)


if __name__ == '__main__':
    unittest.main(verbosity=2)
