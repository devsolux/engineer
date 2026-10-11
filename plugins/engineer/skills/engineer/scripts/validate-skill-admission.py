#!/usr/bin/env python3
'''Validate third-party agent-skill provenance and admission decisions.'''

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from datetime import date
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
from evidence_path import is_under, regular_input_file, relative_posix

HEX40 = re.compile(r'^[0-9a-f]{40}$')
HEX64 = re.compile(r'^[0-9a-f]{64}$')
IDENT = re.compile(r'^[a-z][a-z0-9_]{1,63}$')
VERSION = re.compile(r'^v?\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$')
DANGEROUS = {'shell', 'network', 'read_secrets', 'write_outside_workspace', 'production', 'money', 'hook_admin', 'mcp_admin'}
PERMISSIONS = DANGEROUS | {'read_workspace', 'write_workspace', 'browser_read', 'local_subprocess'}
CAPABILITY_FOR_PERMISSION = {
    'shell': 'execute_shell',
    'network': 'network_access',
    'read_secrets': 'read_secrets',
    'write_outside_workspace': 'external_write',
    'production': 'production_access',
    'money': 'money_actions',
    'hook_admin': 'register_hooks',
    'mcp_admin': 'register_mcp_servers',
}


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative_path(value: Any) -> PurePosixPath | None:
    if not isinstance(value, str) or not value:
        return None
    path = PurePosixPath(value)
    return None if path.is_absolute() or '..' in path.parts or '.' in path.parts else path


def candidate_tree(root: Path) -> tuple[dict[str, tuple[str, str]], list[str]]:
    files: dict[str, tuple[str, str]] = {}
    links: list[str] = []
    for path in sorted(root.rglob('*')):
        name = relative_posix(path, root)
        if '.git' in name.split('/'):
            continue
        if path.is_symlink():
            links.append(name)
        elif path.is_file():
            mode = 'executable' if path.stat().st_mode & 0o111 else 'regular'
            files[name] = (file_hash(path), mode)
    return files, links


def tree_hash(files: dict[str, tuple[str, str]]) -> str:
    rows = [f'{name}\0{digest}\0{mode}\n'.encode() for name, (digest, mode) in sorted(files.items())]
    return hashlib.sha256(b''.join(rows)).hexdigest()


def text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def exact_dependency(item: dict[str, Any]) -> bool:
    version = item.get('version')
    integrity = item.get('integrity')
    integrity_ok = isinstance(integrity, str) and bool(
        re.fullmatch(r'sha256:[0-9a-f]{64}', integrity)
        or re.fullmatch(r'sha512-[A-Za-z0-9+/]+={0,2}', integrity)
    )
    return bool(isinstance(version, str) and (VERSION.fullmatch(version) or HEX40.fullmatch(version)) and integrity_ok)


def validate(data: Any, repo: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    gates: list[str] = []
    if not isinstance(data, dict):
        return ['root must be an object'], []
    root_keys = {'schema_version', 'receipt_kind', 'candidate', 'files', 'dependencies', 'capabilities', 'permissions', 'network_endpoints', 'hooks', 'mcp_servers', 'models', 'analysis', 'sandbox', 'review', 'decision'}
    if set(data) != root_keys:
        errors.append(f'root keys must be exactly {sorted(root_keys)}')
    if data.get('schema_version') != 1:
        errors.append('schema_version must be 1')
    receipt_kind = data.get('receipt_kind')
    if receipt_kind not in {'illustrative_fixture', 'captured_review'}:
        errors.append('receipt_kind must be illustrative_fixture or captured_review')

    candidate = data.get('candidate')
    candidate_keys = {'name', 'author_identity', 'local_path', 'source', 'tree_sha256'}
    if not isinstance(candidate, dict) or set(candidate) != candidate_keys:
        errors.append(f'candidate keys must be exactly {sorted(candidate_keys)}')
        candidate = {}
    for key in ('name', 'author_identity'):
        if not text(candidate.get(key)):
            errors.append(f'candidate.{key} must be non-empty')
    rel = relative_path(candidate.get('local_path'))
    root = repo / rel if rel else None
    files: dict[str, tuple[str, str]] = {}
    links: list[str] = []
    if root is None or not root.is_dir():
        errors.append('candidate.local_path must be an existing repository-relative directory')
    else:
        if not is_under(root, repo):
            errors.append('candidate.local_path escapes the repository')
        else:
            files, links = candidate_tree(root)
    if links:
        errors.append(f'candidate tree contains symlinks: {links}')
    if 'SKILL.md' not in files:
        errors.append('candidate tree must contain SKILL.md')
    claimed_tree = candidate.get('tree_sha256')
    if not isinstance(claimed_tree, str) or not HEX64.fullmatch(claimed_tree):
        errors.append('candidate.tree_sha256 must be lowercase SHA-256')
    elif files and tree_hash(files) != claimed_tree:
        errors.append('candidate.tree_sha256 does not match path, content, and mode')

    source = candidate.get('source')
    source_keys = {'canonical_url', 'owner_verified', 'commit_sha', 'release_label', 'fetched_at'}
    if not isinstance(source, dict) or set(source) != source_keys:
        errors.append(f'candidate.source keys must be exactly {sorted(source_keys)}')
        source = {}
    url = urlparse(source.get('canonical_url')) if isinstance(source.get('canonical_url'), str) else None
    if url is None or url.scheme != 'https' or url.hostname != 'github.com' or url.query or url.fragment or len([part for part in url.path.split('/') if part]) != 2:
        errors.append('candidate.source.canonical_url must be a canonical HTTPS GitHub repository')
    if source.get('owner_verified') is not True:
        gates.append('source owner is not verified')
    if not isinstance(source.get('commit_sha'), str) or not HEX40.fullmatch(source['commit_sha']):
        errors.append('candidate.source.commit_sha must be a full lowercase commit SHA')
    for key in ('release_label', 'fetched_at'):
        if not text(source.get(key)):
            errors.append(f'candidate.source.{key} must be non-empty')

    inventory = data.get('files')
    declared: dict[str, tuple[Any, Any]] = {}
    if not isinstance(inventory, list) or not inventory:
        errors.append('files must be a non-empty array')
        inventory = []
    for index, item in enumerate(inventory):
        label = f'files[{index}]'
        if not isinstance(item, dict) or set(item) != {'path', 'sha256', 'mode', 'purpose', 'reviewed'}:
            errors.append(f'{label} has invalid keys')
            continue
        item_rel = relative_path(item.get('path'))
        if item_rel is None:
            errors.append(f'{label}.path is unsafe')
            continue
        name = item_rel.as_posix()
        if name in declared:
            errors.append(f'duplicate file declaration: {name}')
        declared[name] = (item.get('sha256'), item.get('mode'))
        if not isinstance(item.get('sha256'), str) or not HEX64.fullmatch(item['sha256']) or item.get('mode') not in {'regular', 'executable'}:
            errors.append(f'{label} has invalid hash or mode')
        if not text(item.get('purpose')) or item.get('reviewed') is not True:
            gates.append(f'file is not purpose-documented and reviewed: {name}')
    missing = sorted(set(files) - set(declared))
    extra = sorted(set(declared) - set(files))
    if missing:
        errors.append(f'candidate files missing from inventory: {missing}')
    if extra:
        errors.append(f'inventory paths missing from candidate: {extra}')
    for name in sorted(set(files) & set(declared)):
        if files[name] != declared[name]:
            errors.append(f'file hash or mode mismatch: {name}')

    dependencies = data.get('dependencies')
    if not isinstance(dependencies, list):
        errors.append('dependencies must be an array')
        dependencies = []
    seen_dependencies: set[tuple[Any, Any]] = set()
    dependency_keys = {'ecosystem', 'name', 'version', 'integrity', 'provenance_reviewed', 'lifecycle_scripts'}
    for index, item in enumerate(dependencies):
        if not isinstance(item, dict) or set(item) != dependency_keys:
            errors.append(f'dependencies[{index}] has invalid keys')
            continue
        identity = (item.get('ecosystem'), item.get('name'))
        if identity in seen_dependencies:
            errors.append(f'duplicate dependency: {identity}')
        seen_dependencies.add(identity)
        if item.get('ecosystem') not in {'npm', 'pypi', 'cargo', 'git'} or not text(item.get('name')):
            errors.append(f'dependencies[{index}] has invalid identity')
        if not exact_dependency(item):
            gates.append(f'dependency is not exact and integrity-bound: {identity}')
        lifecycle = item.get('lifecycle_scripts')
        if item.get('provenance_reviewed') is not True or not isinstance(lifecycle, list) or any(not text(value) for value in lifecycle):
            gates.append(f'dependency provenance or lifecycle scripts are unreviewed: {identity}')

    capabilities = data.get('capabilities')
    if not isinstance(capabilities, dict) or set(capabilities) != {'advertised', 'observed'}:
        errors.append('capabilities must contain advertised and observed')
        capabilities = {'advertised': [], 'observed': []}
    for key in ('advertised', 'observed'):
        values = capabilities.get(key)
        if not isinstance(values, list) or any(not isinstance(value, str) or not IDENT.fullmatch(value) for value in values):
            errors.append(f'capabilities.{key} must contain safe identifiers')
        elif len(values) != len(set(values)):
            errors.append(f'capabilities.{key} must be unique')
    shadow = sorted(set(capabilities.get('observed') or []) - set(capabilities.get('advertised') or []))
    if shadow:
        gates.append(f'observed shadow capabilities: {shadow}')

    permissions = data.get('permissions')
    if not isinstance(permissions, dict) or set(permissions) != {'requested', 'dangerous', 'reviewed'}:
        errors.append('permissions has invalid keys')
        permissions = {'requested': [], 'dangerous': []}
    requested = permissions.get('requested')
    dangerous = permissions.get('dangerous')
    if not isinstance(requested, list) or any(value not in PERMISSIONS for value in requested):
        errors.append('permissions.requested contains unknown values')
        requested = []
    if not isinstance(dangerous, list) or set(dangerous) != set(requested) & DANGEROUS:
        errors.append('permissions.dangerous must classify all dangerous requested permissions')
        dangerous = []
    if permissions.get('reviewed') is not True:
        gates.append('permissions are not reviewed')
    advertised = set(capabilities.get('advertised') or [])
    observed = set(capabilities.get('observed') or [])
    for permission in dangerous:
        required_capability = CAPABILITY_FOR_PERMISSION[permission]
        if required_capability not in advertised or required_capability not in observed:
            gates.append(f'dangerous permission lacks advertised and observed capability: {permission}')

    def reviewed_list(key: str, keys: set[str]) -> list[dict[str, Any]]:
        values = data.get(key)
        if not isinstance(values, list):
            errors.append(f'{key} must be an array')
            return []
        valid: list[dict[str, Any]] = []
        for index, item in enumerate(values):
            if not isinstance(item, dict) or set(item) != keys:
                errors.append(f'{key}[{index}] has invalid keys')
            else:
                valid.append(item)
                if item.get('reviewed') is not True:
                    gates.append(f'{key}[{index}] is unreviewed')
        return valid

    endpoints = reviewed_list('network_endpoints', {'url', 'purpose', 'reviewed'})
    for index, item in enumerate(endpoints):
        endpoint = urlparse(item.get('url')) if isinstance(item.get('url'), str) else None
        if endpoint is None or endpoint.scheme != 'https' or not endpoint.hostname or not text(item.get('purpose')):
            errors.append(f'network_endpoints[{index}] must have HTTPS URL and purpose')
    hooks = reviewed_list('hooks', {'event', 'command', 'purpose', 'reviewed'})
    servers = reviewed_list('mcp_servers', {'name', 'command', 'permissions', 'purpose', 'reviewed'})
    models = reviewed_list('models', {'path', 'sha256', 'license', 'purpose', 'reviewed'})
    if endpoints and 'network' not in requested:
        gates.append('network endpoints lack requested network permission')
    for index, item in enumerate(hooks):
        if any(not text(item.get(key)) for key in ('event', 'command', 'purpose')):
            errors.append(f'hooks[{index}] needs event, command, and purpose')
    for index, item in enumerate(servers):
        if any(not text(item.get(key)) for key in ('name', 'command', 'purpose')) or not isinstance(item.get('permissions'), list):
            errors.append(f'mcp_servers[{index}] needs name, command, permissions, and purpose')
    if hooks and 'hook_admin' not in requested:
        gates.append('hooks lack requested hook_admin permission')
    if servers and 'mcp_admin' not in requested:
        gates.append('MCP servers lack requested mcp_admin permission')
    for index, item in enumerate(models):
        model_rel = relative_path(item.get('path'))
        name = model_rel.as_posix() if model_rel else None
        if name not in files or item.get('sha256') != (files.get(name) or (None,))[0]:
            errors.append(f'models[{index}] path and hash must match an inventoried file')
        if not text(item.get('license')) or not text(item.get('purpose')):
            errors.append(f'models[{index}] needs license and purpose')
    if models and ('local_model_inference' not in advertised or 'local_model_inference' not in observed):
        gates.append('bundled models lack advertised and observed local_model_inference capability')

    analysis = data.get('analysis')
    analysis_keys = {'instruction_review', 'code_review', 'obfuscation_scan', 'dependency_steering_review', 'secret_scan', 'permission_review', 'scanner_results'}
    if not isinstance(analysis, dict) or set(analysis) != analysis_keys:
        errors.append(f'analysis keys must be exactly {sorted(analysis_keys)}')
        analysis = {}
    for key in analysis_keys - {'scanner_results'}:
        if not isinstance(analysis.get(key), bool):
            errors.append(f'analysis.{key} must be boolean')
        elif analysis.get(key) is not True:
            gates.append(f'analysis gate failed: {key}')
    results = analysis.get('scanner_results')
    if not isinstance(results, list) or len(results) < 2:
        errors.append('analysis.scanner_results requires at least two results')
    else:
        for index, item in enumerate(results):
            if not isinstance(item, dict) or set(item) != {'tool', 'version', 'result'} or item.get('result') not in {'pass', 'fail'}:
                errors.append(f'analysis.scanner_results[{index}] is invalid')
            elif item.get('result') == 'fail':
                gates.append(f'scanner failed: {item.get("tool")}')

    sandbox = data.get('sandbox')
    sandbox_keys = {'disposable', 'network_policy', 'synthetic_secrets', 'filesystem_observed', 'processes_observed', 'cleanup_verified', 'cases'}
    if not isinstance(sandbox, dict) or set(sandbox) != sandbox_keys:
        errors.append(f'sandbox keys must be exactly {sorted(sandbox_keys)}')
        sandbox = {}
    for key in ('disposable', 'synthetic_secrets', 'filesystem_observed', 'processes_observed', 'cleanup_verified'):
        if not isinstance(sandbox.get(key), bool):
            errors.append(f'sandbox.{key} must be boolean')
        elif sandbox.get(key) is not True:
            gates.append(f'sandbox gate failed: {key}')
    if sandbox.get('network_policy') not in {'deny', 'simulated'}:
        errors.append('sandbox.network_policy must be deny or simulated')
    cases = sandbox.get('cases')
    classes: set[str] = set()
    if not isinstance(cases, list) or not cases:
        errors.append('sandbox.cases must be non-empty')
        cases = []
    for index, item in enumerate(cases):
        case_keys = {'id', 'class', 'result', 'exfiltration_observed', 'unexpected_capabilities'}
        if not isinstance(item, dict) or set(item) != case_keys:
            errors.append(f'sandbox.cases[{index}] has invalid keys')
            continue
        classes.add(item.get('class'))
        if item.get('class') not in {'benign', 'adversarial'} or item.get('result') not in {'pass', 'fail'}:
            errors.append(f'sandbox.cases[{index}] has invalid class or result')
        if item.get('result') != 'pass' or item.get('exfiltration_observed') is not False or item.get('unexpected_capabilities') != []:
            gates.append(f'sandbox case failed or observed unexpected behavior: {item.get("id")}')
    if classes != {'benign', 'adversarial'}:
        gates.append('sandbox requires benign and adversarial cases')

    review = data.get('review')
    review_keys = {'primary_reviewer', 'independent_reviewer', 'reviewed_at', 'review_by'}
    if not isinstance(review, dict) or set(review) != review_keys:
        errors.append('review has invalid keys')
        review = {}
    identities = {candidate.get('author_identity'), review.get('primary_reviewer'), review.get('independent_reviewer')}
    if len(identities) != 3 or any(not text(value) for value in identities):
        gates.append('candidate author and both reviewers must be distinct named identities')
    try:
        reviewed_at = date.fromisoformat(review.get('reviewed_at', ''))
        review_by = date.fromisoformat(review.get('review_by', ''))
        if review_by <= reviewed_at:
            errors.append('review.review_by must be after reviewed_at')
        elif review_by < date.today():
            gates.append('admission review has expired')
    except (TypeError, ValueError):
        errors.append('review dates must use YYYY-MM-DD')

    decision = data.get('decision')
    decision_keys = {'status', 'reasons', 'accepted_risks', 'unresolved_risks', 'owner', 'rollback'}
    if not isinstance(decision, dict) or set(decision) != decision_keys:
        errors.append('decision has invalid keys')
        decision = {}
    status = decision.get('status')
    if status not in {'reject', 'quarantine', 'trust'}:
        errors.append('decision.status must be reject, quarantine, or trust')
    for key in ('reasons', 'accepted_risks', 'unresolved_risks'):
        values = decision.get(key)
        if not isinstance(values, list) or (key == 'reasons' and not values) or any(not text(value) for value in values):
            errors.append(f'decision.{key} must be a valid string array')
    for key in ('owner', 'rollback'):
        if not text(decision.get(key)):
            errors.append(f'decision.{key} must be non-empty')
    if status == 'trust':
        if receipt_kind != 'captured_review':
            errors.append('trust requires receipt_kind captured_review')
        required_acceptances = set(dangerous)
        if models:
            required_acceptances.add('bundled_models')
        accepted = set(decision.get('accepted_risks') or [])
        if accepted != required_acceptances:
            errors.append(f'decision.accepted_risks must exactly match reviewed elevated risks: {sorted(required_acceptances)}')
        if endpoints and sandbox.get('network_policy') != 'simulated':
            errors.append('trusted networked skills require simulated allowlisted egress evidence')
        if gates:
            errors.append(f'trust decision contradicts failed gates: {sorted(set(gates))}')
        if decision.get('unresolved_risks') != []:
            errors.append('trust decision requires no unresolved risks')
    elif status in {'reject', 'quarantine'} and not gates and decision.get('unresolved_risks') == []:
        errors.append(f'{status} decision requires a failed gate or unresolved risk')
    return errors, sorted(set(gates))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('path', type=Path)
    parser.add_argument('--json', action='store_true')
    args = parser.parse_args()
    try:
        path = regular_input_file(args.path)
        if path is None: raise ValueError('path must be a regular file, not a symlink')
        data = json.loads(path.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        errors, gates = [f'cannot read valid JSON: {exc}'], []
    else:
        errors, gates = validate(data, Path.cwd().resolve())
    result = {'ok': not errors, 'errors': errors, 'failed_gates': gates}
    if args.json:
        print(json.dumps(result, indent=2))
    elif errors:
        print('skill admission invalid:', file=sys.stderr)
        for error in errors:
            print(f'- {error}', file=sys.stderr)
    else:
        print('skill admission valid')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
