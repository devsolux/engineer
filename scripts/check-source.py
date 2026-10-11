#!/usr/bin/env python3
"""Offline syntax, local links, and packaging identity checks (no execution)."""
from __future__ import annotations
import ast
import json
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET
try:
    import yaml
except ImportError:
    print("FAIL PyYAML 6.0.3 is required for source validation; use make setup", file=sys.stderr)
    raise SystemExit(1)

class UniqueLoader(yaml.SafeLoader):
    """Reject ambiguous duplicate mapping keys in configuration files."""
    pass

def unique_mapping(loader, node, deep=False):
    mapping = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping

UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, unique_mapping)

ROOT = Path(__file__).resolve().parent.parent


def main() -> int:
    errors = []
    count = 0
    for path in sorted(ROOT.rglob('*')):
        rel = path.relative_to(ROOT)
        if any(p in {'.git', '.venv', '.build', 'dist', 'plugins', '__pycache__', 'node_modules', '.engineer'} for p in rel.parts):
            continue
        if not path.is_file():
            continue
        try:
            if path.suffix == '.py':
                ast.parse(path.read_text(), filename=str(rel))
            elif path.suffix == '.sh':
                result = subprocess.run(['bash', '-n', str(path)], capture_output=True, text=True)
                if result.returncode:
                    raise ValueError(result.stderr.strip())
            elif path.suffix == '.json':
                json.loads(path.read_text())
            elif path.suffix in {'.yaml', '.yml'}:
                list(yaml.load_all(path.read_text(), Loader=UniqueLoader))
            elif path.suffix == '.svg':
                ET.fromstring(path.read_bytes())
            else:
                continue
            count += 1
        except (ValueError, TypeError, SyntaxError, OSError, ET.ParseError, yaml.YAMLError) as exc:
            errors.append(f'{rel}: {exc}')
    for rel in ('README.md', 'COMPAT.md', 'CONTRIBUTING.md', 'CHANGELOG.md'):
        path = ROOT / rel
        if not path.is_file():
            errors.append('required document missing: ' + rel)
            continue
        for target in re.findall(r'\]\(([^)\s]+)(?:\s+[^)]*)?\)', path.read_text()):
            if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
                continue
            resolved = path.parent / target.split('#')[0]
            if not resolved.exists():
                errors.append(f'{rel}: broken local link: {target}')
    try:
        claude = json.loads((ROOT / '.claude-plugin/marketplace.json').read_text())
        codex = json.loads((ROOT / '.agents/plugins/marketplace.json').read_text())
        for host, value in (('Claude', claude), ('Codex', codex)):
            if value.get('name') != 'devsolux-engineer' or len(value.get('plugins', [])) != 1:
                errors.append(host + ': incorrect marketplace identity')
            if value['plugins'][0]['name'] != 'engineer':
                errors.append(host + ': incorrect plugin identity')
        if claude['plugins'][0]['source'] != './plugins/engineer':
            errors.append('Claude: incorrect source path')
        if codex['plugins'][0]['source'] != {'source': 'local', 'path': './plugins/engineer'}:
            errors.append('Codex: incorrect source path')
    except (OSError, ValueError, KeyError, IndexError, TypeError) as exc:
        errors.append('marketplace manifests: ' + str(exc))
    if errors:
        print('\n'.join('FAIL ' + error for error in errors))
        return 1
    print(f'PASS syntax/structure: {count} files; local links and marketplace identity')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
