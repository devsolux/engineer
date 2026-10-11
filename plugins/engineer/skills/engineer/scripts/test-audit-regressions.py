#!/usr/bin/env python3
"""Regression coverage for malformed input, paths, scanner failures, and health."""
from pathlib import Path
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

from evidence_path import safe_path
ROOT = Path(__file__).resolve().parent.parent


class AuditRegressionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='engineer-audit-test-')
        self.addCleanup(self.temp.cleanup)
        # safe_path returns resolved paths; macOS exposes /var as /private/var.
        self.root = Path(self.temp.name).resolve()
        self.env = dict(os.environ, ENGINEER_FORCE_GREP='1', PYTHONDONTWRITEBYTECODE='1')

    def scan(self, *args, env=None):
        return subprocess.run(['bash', str(ROOT / 'scripts/engineer-scan.sh'), *args], cwd=self.root,
                              env=env or self.env, capture_output=True, text=True)

    def test_scanner_unknown_args_and_json_stdout(self):
        self.assertEqual(self.scan('--not-real').returncode, 2)
        result = self.scan('--backend', '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(json.loads(result.stdout)['ok'])

    def test_strict_alone_keeps_design_coverage(self):
        (self.root / 'page.tsx').write_text('export const View = () => <p className="text-red-500">Hello</p>;\n')
        result = self.scan('--strict', '--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['ok'])

    def test_grep_brace_globs_check_local_storage(self):
        (self.root / 'auth.ts').write_text('localStorage.setItem("token", token);\n')
        result = self.scan('--backend', '--strict', '--json')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('localStorage', result.stderr)
        self.assertFalse(json.loads(result.stdout)['ok'])

    def test_search_backend_errors_never_become_clean(self):
        tools = self.root / 'bin'
        tools.mkdir()
        fake = tools / 'rg'
        fake.write_text('#!/bin/sh\necho "synthetic read failure" >&2\nexit 2\n')
        fake.chmod(0o755)
        env = dict(self.env, ENGINEER_FORCE_GREP='0', PATH=str(tools) + os.pathsep + os.environ['PATH'])
        result = self.scan('--backend', '--json', env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertIn('coverage is incomplete', result.stderr)

    def test_portable_evidence_paths(self):
        for value in ('../escape', '/absolute', 'C:/windows', 'C:relative', 'a\\b', 'a\0b'):
            with self.subTest(value=value):
                self.assertIsNone(safe_path(value, self.root))
        (self.root / 'real').write_text('ok')
        (self.root / 'link').symlink_to(self.root / 'real')
        self.assertIsNone(safe_path('link', self.root))
        self.assertEqual(safe_path('real', self.root), self.root / 'real')

    def test_malformed_eval_banks_are_diagnostics_not_tracebacks(self):
        bank = json.loads((ROOT / 'evals/evals.json').read_text())
        bad_id = copy.deepcopy(bank)
        bad_id['evals'][0]['id'] = {'invalid': 'unhashable'}
        for value in ([], None, {'skill_name': 'engineer', 'evals': {}}, bad_id):
            with self.subTest(value=type(value).__name__):
                path = self.root / 'bank.json'
                path.write_text(json.dumps(value))
                result = subprocess.run(['bash', str(ROOT / 'scripts/run-evals.sh'), '--file', str(path)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('FAIL eval bank', result.stdout)
                self.assertNotIn('Traceback', result.stderr)

    def test_health_is_strict_only_on_request_without_test_suppression(self):
        (self.root / 'package.json').write_text('{"scripts":{"test":"intentional-test-command"}}')
        (self.root / 'pnpm-lock.yaml').write_text('lockfileVersion: 9\n')
        tools = self.root / 'bin'
        tools.mkdir()
        fake = tools / 'pnpm'
        fake.write_text('#!/bin/sh\nprintf "%s\\n" "$@" >> "$CALLS"\nexit 1\n')
        fake.chmod(0o755)
        calls = self.root / 'calls.txt'
        env = dict(self.env, PATH=str(tools) + os.pathsep + os.environ['PATH'], CALLS=str(calls))
        command = ['bash', str(ROOT / 'scripts/engineer-health.sh'), '--profile', 'app', '--json']
        for strict, expected in ((False, 0), (True, 1)):
            result = subprocess.run(command + (['--strict'] if strict else []), cwd=self.root, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, expected, result.stderr)
            self.assertFalse(json.loads(result.stdout)['ok'])
        self.assertEqual(calls.read_text().splitlines(), ['test', 'test'])

    def test_commands_do_not_suppress_verification(self):
        for path in (ROOT / 'commands').glob('*.md'):
            self.assertNotIn('|| true', path.read_text(), path.name)
            self.assertNotIn('2>/dev/null', path.read_text(), path.name)


if __name__ == '__main__':
    unittest.main(verbosity=2)
