#!/usr/bin/env python3
"""Build the two host packages from one canonical skill; standard library only.

No network, host installation, model calls, or source/fixture rewriting. The
checked-in generated bundle makes Git marketplace installs build-hook-free.
Existing generated files are replaced only after checking their recorded hash
and mode. Unexpected files and user modifications are never deleted silently.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parent.parent
MARKER = '.engineer-build.json'
INCLUDE = ('SKILL.md', 'COMPAT.md', 'LICENSE', 'SECURITY.md', 'agents', 'assets',
           'commands', 'references', 'scripts', 'templates', 'docs')
EXCLUDE = {'__pycache__', 'node_modules', '.venv', '.git', '.engineer'}
# Desktop metadata (Finder/Explorer) is never bundle content; ignoring it keeps
# drift checks and rebuilds working after a generated tree is browsed locally.
OS_METADATA = {'.DS_Store', 'Thumbs.db', 'desktop.ini'}


def encoded(value: object) -> bytes:
    return (json.dumps(value, indent=2, ensure_ascii=False) + '\n').encode()


def version(root: Path) -> str:
    match = re.search(r'^  version: "([0-9]+\.[0-9]+\.[0-9]+)"$',
                      (root / 'SKILL.md').read_text(encoding='utf-8'), re.M)
    if not match:
        raise ValueError('SKILL.md must declare metadata.version as a semver string')
    return match[1]


def is_os_metadata(name: str) -> bool:
    return name in OS_METADATA or name.startswith('._')


def command_description(path: Path) -> str:
    """Return the canonical command's frontmatter description (required)."""
    text = path.read_text(encoding='utf-8')
    match = re.match(r'---\n(.*?)\n---\n', text, re.S)
    for line in (match[1].splitlines() if match else ()):
        if line.startswith('description:'):
            value = line.split(':', 1)[1].strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in '"\'':
                value = value[1:-1].strip()
            if value:
                return value
    raise ValueError(f'command frontmatter must declare a description: commands/{path.name}')


def source_files(root: Path):
    for entry in INCLUDE:
        base = root / entry
        if not base.exists() or base.is_symlink():
            raise ValueError(f'missing or symlinked bundle input: {entry}')
        for path in ([base] if base.is_file() else sorted(base.rglob('*'))):
            rel = path.relative_to(root)
            if any(p in EXCLUDE or is_os_metadata(p) for p in rel.parts):
                continue
            if path.is_symlink():
                raise ValueError(f'symlink in bundle input: {rel}')
            if path.is_dir():
                continue
            if not path.is_file():
                raise ValueError(f'non-regular bundle input: {rel}')
            if path.suffix in {'.pyc', '.pyo'} or path.name.startswith('.env'):
                continue
            yield rel.as_posix(), path


def render(root: Path) -> dict[str, tuple[bytes, int]]:
    meta = json.loads((root / 'packaging/plugin.json').read_text(encoding='utf-8'))
    allowed = {'$schema', 'name', 'description', 'author', 'homepage', 'repository', 'license', 'keywords'}
    if not isinstance(meta, dict) or set(meta) - allowed:
        raise ValueError('packaging/plugin.json contains unsupported fields')
    if meta.get('$schema') != 'https://agent-plugins.org/schemas/1.0.0/plugin.schema.json':
        raise ValueError('incorrect portable plugin schema identifier')
    if meta.get('repository') != 'https://github.com/devsolux/engineer':
        raise ValueError('repository must be devsolux/engineer')
    if meta.get('name') != 'engineer' or 'version' in meta:
        raise ValueError('packaging metadata must name engineer; version belongs only in SKILL.md')
    meta['version'] = version(root)
    meta['extensions'] = {'com.openai': {'interface': {
        'displayName': 'Engineer',
        'shortDescription': 'Full-stack engineering workflows and verification tools',
        'longDescription': meta['description']}}}
    claude = {k: v for k, v in meta.items()
              if k in {'name', 'version', 'description', 'author', 'homepage', 'repository', 'license', 'keywords'}}
    codex = {**claude, 'skills': './skills/', 'interface': meta['extensions']['com.openai']['interface']}
    result = {'plugin.json': (encoded(meta), 0o644),
              '.claude-plugin/plugin.json': (encoded(claude), 0o644),
              '.codex-plugin/plugin.json': (encoded(codex), 0o644),
              'LICENSE': ((root / 'LICENSE').read_bytes(), 0o644),
              'README.md': (b'# Engineer plugin\n\nGenerated from the canonical devsolux/engineer sources.\n'
                            b'Read skills/engineer/SKILL.md; do not edit this generated tree.\n'
                            b'This package contains skills and tools, not an MCP server.\n\n'
                            b'Research notes, the eval bank, and maintainer suites (make check/test)\n'
                            b'live only in the source repository: https://github.com/devsolux/engineer\n', 0o644)}
    for rel, path in source_files(root):
        result['skills/engineer/' + rel] = (path.read_bytes(), 0o755 if path.stat().st_mode & 0o111 else 0o644)
    for path in sorted((root / 'commands').glob('engineer-*.md')):
        verb = path.stem.removeprefix('engineer-')
        # Use literal absolute host substitution; no relative traversal or tool grants.
        content = ('---\ndescription: ' + json.dumps(command_description(path), ensure_ascii=False)
                   + '\n---\n\n'
                   'Read `${CLAUDE_PLUGIN_ROOT}/skills/engineer/SKILL.md`, then '
                   '`${CLAUDE_PLUGIN_ROOT}/skills/engineer/commands/' + path.name + '`.\n'
                   'Resolve ENGINEER to `${CLAUDE_PLUGIN_ROOT}/skills/engineer` when running bundled tools.\n'
                   'Follow the loaded workflow for this task, preserving repository instructions, '
                   'permission boundaries, and required approvals.\n\nTask: $ARGUMENTS\n')
        result['commands/' + verb + '.md'] = (content.encode(), 0o644)
    hashes = {name: {'sha256': hashlib.sha256(data).hexdigest(), 'mode': mode}
              for name, (data, mode) in sorted(result.items())}
    result[MARKER] = (encoded({'format': 1, 'generator': 'scripts/build-plugin.py',
                               'version': version(root), 'files': hashes}), 0o644)
    return result


def actual_files(target: Path) -> dict[str, tuple[bytes, int]]:
    actual = {}
    if target.is_symlink():
        raise ValueError('refusing symlinked output directory')
    for path in sorted(target.rglob('*')):
        if is_os_metadata(path.name):
            continue
        if path.is_symlink():
            raise ValueError(f'refusing symlink in output: {path}')
        if path.is_file():
            # Git records only the executable bit; checkouts apply the user's umask (e.g. 0664).
            mode = 0o755 if path.stat().st_mode & 0o111 else 0o644
            actual[path.relative_to(target).as_posix()] = (path.read_bytes(), mode)
        elif not path.is_dir():
            raise ValueError(f'non-regular output: {path}')
    return actual


def ensure_owned(target: Path) -> None:
    if not target.exists():
        return
    actual = actual_files(target)
    if MARKER not in actual:
        raise ValueError(f'refusing to overwrite unowned directory: {target}')
    marker = json.loads(actual[MARKER][0])
    if marker.get('format') != 1 or marker.get('generator') != 'scripts/build-plugin.py':
        raise ValueError('unrecognized generated bundle marker')
    expected = marker.get('files')
    if not isinstance(expected, dict) or set(actual) != set(expected) | {MARKER}:
        raise ValueError('generated bundle has unexpected/missing files; preserve your changes before rebuilding')
    for name, (data, mode) in actual.items():
        if name == MARKER:
            continue
        if expected[name] != {'sha256': hashlib.sha256(data).hexdigest(), 'mode': mode}:
            raise ValueError(f'locally modified generated file: {name}; edit canonical source instead')


def drift_summary(desired: dict[str, tuple[bytes, int]], actual: dict[str, tuple[bytes, int]]) -> str:
    """Name the drifted paths (bounded) so a failed check is actionable."""
    groups = (('missing', sorted(set(desired) - set(actual))),
              ('unexpected', sorted(set(actual) - set(desired))),
              ('changed', sorted(n for n in set(desired) & set(actual) if desired[n] != actual[n])))
    parts = []
    for label, names in groups:
        if names:
            shown = ', '.join(names[:5]) + (f' (+{len(names) - 5} more)' if len(names) > 5 else '')
            parts.append(f'{label}: {shown}')
    return '; '.join(parts)


def build(root: Path, check: bool = False) -> Path:
    target = root / 'plugins/engineer'
    if (root / 'plugins').is_symlink():
        raise ValueError('refusing symlinked plugins directory')
    desired = render(root)
    if check:
        if not target.is_dir():
            raise ValueError('plugin bundle drift (missing: plugins/engineer); run make build and review generated changes')
        actual = actual_files(target)
        if actual != desired:
            raise ValueError(f'plugin bundle drift ({drift_summary(desired, actual)}); '
                             'run make build and review generated changes')
        return target
    ensure_owned(target)
    target.parent.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.engineer-stage-', dir=target.parent) as stage:
        staged = Path(stage) / 'engineer'
        staged.mkdir()
        for name, (data, mode) in desired.items():
            path = staged / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            path.chmod(mode)
        backup = Path(stage) / 'previous'
        if target.exists():
            target.rename(backup)
        try:
            staged.rename(target)
        except BaseException:
            if backup.exists():
                backup.rename(target)
            raise
    return target


def package(root: Path, target: Path) -> Path:
    dist = root / 'dist'
    if dist.is_symlink():
        raise ValueError('refusing symlinked dist directory')
    dist.mkdir(exist_ok=True)
    filename = dist / ('engineer-' + version(root) + '-plugin.zip')
    if filename.is_symlink():
        raise ValueError('refusing symlinked archive destination')
    with tempfile.TemporaryDirectory(prefix='.engineer-package-', dir=dist) as tmp:
        staged = Path(tmp) / filename.name
        with zipfile.ZipFile(staged, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, (data, mode) in sorted(actual_files(target).items()):
                info = zipfile.ZipInfo(name, date_time=(2026, 10, 11, 0, 0, 0))
                info.create_system = 3
                info.external_attr = (0o100000 | mode) << 16
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        os.replace(staged, filename)
    checksum = filename.with_suffix(filename.suffix + '.sha256')
    if checksum.is_symlink():
        raise ValueError('refusing symlinked checksum destination')
    checksum.write_text(hashlib.sha256(filename.read_bytes()).hexdigest() + '  ' + filename.name + '\n')
    return filename


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true', help='read-only drift check')
    parser.add_argument('--package', action='store_true', help='build a reproducible plugin ZIP')
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args()
    if args.check and args.package:
        parser.error('--check and --package are mutually exclusive')
    try:
        root = args.root.resolve(strict=True)
        target = build(root, args.check)
        print(('Verified ' if args.check else 'Built ') + str(target))
        if args.package:
            print('Packaged ' + str(package(root, target)))
        return 0
    except (OSError, ValueError, TypeError, KeyError) as exc:
        print(f'plugin build: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
