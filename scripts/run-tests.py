#!/usr/bin/env python3
"""Discover and run every offline shell/Python fixture; never runs live evals.

Each suite gets a fresh source snapshot and an empty HOME so temporary writes,
negative fixtures, and parallel suites cannot interfere with each other or with
real host configuration. Logs/results are local build artifacts.
"""
from __future__ import annotations
import argparse
import concurrent.futures
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent.parent
# Host profile overrides would redirect fixtures into real configuration directories.
PROFILE_VARIABLES = {'CLAUDE_CONFIG_DIR', 'CODEX_HOME', 'HERMES_HOME', 'XDG_CONFIG_HOME',
                     'GIT_CONFIG_GLOBAL', 'ENGINEER'}


def discover(root: Path = ROOT) -> list[Path]:
    return sorted(p for p in (root / 'scripts').glob('test-*')
                  if p.suffix in {'.sh', '.py'} and p.is_file() and not p.is_symlink())


def run_one(test: Path, timeout: int, logs: Path) -> dict:
    start = time.monotonic()
    with tempfile.TemporaryDirectory(prefix='engineer-test-') as work:
        root = Path(work) / 'repo'
        shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(
            '.git', '.venv', '__pycache__', '*.pyc', '.build', 'dist', '.engineer', 'node_modules'),
            symlinks=True)
        home = Path(work) / 'home'
        home.mkdir()
        env = {key: value for key, value in os.environ.items() if key not in PROFILE_VARIABLES}
        env.update(PYTHONDONTWRITEBYTECODE='1', LC_ALL='C', HOME=str(home),
                   PATH=str(Path(sys.executable).parent) + os.pathsep + os.environ.get('PATH', ''))
        cmd = (['bash'] if test.suffix == '.sh' else [sys.executable]) + [str(root / 'scripts' / test.name)]
        log_path = logs / (test.name + '.log')
        timed_out = False
        with log_path.open('w') as log:
            process = subprocess.Popen(cmd, cwd=root, env=env, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=(os.name == 'posix'))
            try:
                code = process.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                if os.name == 'posix':
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
                process.wait()
                code = 124
                log.write('\nFAIL: suite timed out\n')
        return {'suite': test.name, 'exit_code': code, 'timed_out': timed_out,
                'seconds': round(time.monotonic() - start, 3), 'log': log_path.name}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true')
    parser.add_argument('--select', action='append', default=[], help='exact suite basename; repeatable')
    parser.add_argument('--jobs', type=int, default=1)
    parser.add_argument('--timeout', type=int, default=180)
    parser.add_argument('--output', type=Path, default=ROOT / '.build/tests')
    args = parser.parse_args()
    tests = discover()
    if args.select:
        unknown = set(args.select) - {p.name for p in tests}
        if unknown:
            parser.error('unknown test suites: ' + ', '.join(sorted(unknown)))
        tests = [p for p in tests if p.name in args.select]
    if not tests or args.jobs < 1 or args.timeout < 1:
        parser.error('at least one suite, positive jobs and timeout are required')
    if args.list:
        print('\n'.join(p.name for p in tests))
        return 0
    if args.output.is_symlink():
        parser.error('output must not be a symlink')
    args.output.mkdir(parents=True, exist_ok=True)
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as pool:
        futures = [pool.submit(run_one, p, args.timeout, args.output) for p in tests]
        for future in concurrent.futures.as_completed(futures):
            result = future.result()
            results.append(result)
            print(f"{'PASS' if result['exit_code'] == 0 else 'FAIL'} {result['suite']} ({result['seconds']}s)", flush=True)
    results.sort(key=lambda item: item['suite'])
    failed = sum(r['exit_code'] != 0 for r in results)
    report = {'kind': 'offline-fixture-suites', 'live_host_execution': False,
              'total': len(results), 'passed': len(results) - failed, 'failed': failed, 'results': results}
    (args.output / 'results.json').write_text(json.dumps(report, indent=2) + '\n')
    print(f"{report['passed']}/{report['total']} offline suites passed; report: {args.output / 'results.json'}")
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
