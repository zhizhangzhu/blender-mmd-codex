"""Read-only studio evidence registry. Structural checks are not art approval."""
import argparse
import hashlib
import json
from pathlib import Path, PureWindowsPath
import re
ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / 'catalog/studio.json'
LIMITS = 'Structural checks are not art approval; transfer scope claims require human review.'

def load(path=DEFAULT):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()

def validate(data, root=ROOT, check_artifacts=False):
    errors = []
    root = Path(root).resolve()

    def bad(where, message):
        errors.append(f'{where}: {message}')

    def string(v):
        return isinstance(v, str) and bool(v.strip())

    def path(v, where):
        if not string(v):
            bad(where, 'expected repository path')
            return
        p = (root / v).resolve()
        if Path(v).is_absolute() or PureWindowsPath(v).is_absolute() or (not p.is_relative_to(root)):
            bad(where, 'path escapes repository')
        elif not p.is_file():
            bad(where, 'file does not exist')

    def strings(v, where):
        if not isinstance(v, list) or any((not string(x) for x in v)):
            bad(where, 'expected string list')
            return []
        return v

    def artifacts(v, where):
        if not isinstance(v, list):
            bad(where, 'expected artifact list')
            return []
        for a in v:
            if not isinstance(a, dict):
                bad(where, 'expected artifact object')
                continue
            if not string(a.get('path')):
                bad(where, 'missing artifact path')
                continue
            if not isinstance(a.get('sha256'), str) or not re.fullmatch('[0-9a-fA-F]{64}', a['sha256']):
                bad(where, 'invalid sha256')
            if check_artifacts:
                p = Path(a['path'])
                if not p.is_absolute():
                    p = root / p
                try:
                    if digest(p).lower() != str(a.get('sha256')).lower():
                        bad(where, 'artifact hash mismatch')
                except OSError as e:
                    bad(where, f'artifact unavailable: {e}')
        return v
    if not isinstance(data, dict):
        return ['registry: expected object']
    if type(data.get('schema_version')) is not int or data['schema_version'] != 1:
        bad('schema_version', 'expected 1')
    groups = {}
    for group in ('capabilities', 'preferences', 'curriculum'):
        records = data.get(group)
        if not isinstance(records, list):
            bad(group, 'expected list')
            records = []
        groups[group] = [x for x in records if isinstance(x, dict)]
        if len(groups[group]) != len(records):
            bad(group, 'expected record objects')
        ids = []
        for x in groups[group]:
            if not string(x.get('id')):
                bad(group, 'missing id')
            else:
                ids.append(x['id'])
        if len(ids) != len(set(ids)):
            bad(group, 'duplicate IDs')
    for c in groups['capabilities']:
        w = str(c.get('id'))
        for k in ('title', 'route', 'problem', 'when_to_use', 'next_exercise'):
            if not string(c.get(k)):
                bad(w, f'missing {k}')
        for k in ('tags', 'avoid_when', 'method', 'entrypoints', 'knowledge'):
            for v in strings(c.get(k), w + '.' + k):
                if k in ('entrypoints', 'knowledge'):
                    path(v, w + '.' + k)
        if c.get('art_status') not in ('pending', 'revision_requested', 'approved'):
            bad(w, 'invalid art_status')
        feedback = c.get('user_feedback_provenance')
        if feedback is not None:
            path(feedback, w + '.user_feedback_provenance')
        if c.get('art_status') == 'approved' and (not feedback):
            bad(w, 'approval requires user feedback provenance')
        if c.get('transfer_level') not in ('single_case', 'same_class', 'cross_project'):
            bad(w, 'invalid transfer_level')
        evidence = c.get('evidence')
        if not isinstance(evidence, list):
            bad(w, 'expected evidence list')
            evidence = []
        transfer = False
        for e in evidence:
            if not isinstance(e, dict):
                bad(w, 'expected evidence object')
                continue
            if e.get('dimension') not in ('reading', 'still', 'motion', 'reopen', 'integration', 'transfer'):
                bad(w, 'invalid evidence dimension')
            if e.get('result') not in ('passed', 'failed', 'untested'):
                bad(w, 'invalid evidence result')
            if not string(e.get('scope')):
                bad(w, 'evidence requires scope/reason')
            path(e.get('provenance'), w + '.evidence.provenance')
            aa = artifacts(e.get('artifacts'), w + '.evidence')
            if e.get('result') == 'passed' and (not aa):
                bad(w, 'passed evidence requires artifacts')
            if e.get('dimension') == 'transfer' and e.get('result') == 'passed' and (len({a.get('path') for a in aa if isinstance(a, dict) and string(a.get('path'))}) >= 2):
                transfer = True
        if c.get('transfer_level') in ('same_class', 'cross_project') and (not transfer):
            bad(w, 'same_class/cross_project requires passed transfer with two distinct case artifacts')
    for p in groups['preferences']:
        w = str(p.get('id'))
        for k in ('statement', 'scope'):
            if not string(p.get(k)):
                bad(w, f'missing {k}')
        source = p.get('source')
        if not isinstance(source, dict):
            bad(w, 'expected source object')
        else:
            if source.get('kind') not in ('user_instruction', 'user_feedback'):
                bad(w, 'invalid source kind')
            path(source.get('provenance'), w + '.source')
        strings(p.get('exceptions'), w + '.exceptions')
        for a in artifacts(p.get('examples'), w + '.examples'):
            if isinstance(a, dict) and a.get('role') not in ('positive', 'negative', 'context'):
                bad(w, 'invalid example role')
    caps = {c.get('id') for c in groups['capabilities'] if string(c.get('id'))}
    graph = {}
    for c in groups['curriculum']:
        w = str(c.get('id'))
        for k in ('title', 'route', 'exercise'):
            if not string(c.get(k)):
                bad(w, f'missing {k}')
        strings(c.get('acceptance'), w + '.acceptance')
        graph[w] = strings(c.get('prerequisites'), w + '.prerequisites')
        for v in strings(c.get('capability_ids'), w + '.capability_ids'):
            if v not in caps:
                bad(w, 'dangling capability ' + v)
    visiting, done = (set(), set())

    def visit(n):
        if n in visiting:
            bad(n, 'cyclic prerequisites')
            return
        if n in done:
            return
        visiting.add(n)
        for v in graph[n]:
            if v not in graph:
                bad(n, 'dangling prerequisite ' + v)
            else:
                visit(v)
        visiting.remove(n)
        done.add(n)
    for n in graph:
        visit(n)
    return errors

def select_capabilities(data, query='', route=None, limit=3):
    tokens = query.casefold().split()

    def score(c):
        text = ' '.join([c['title'], c['problem'], *c['tags']]).casefold()
        return sum((t in text for t in tokens)) + sum((len(tag.strip()) >= 2 and tag.casefold() in query.casefold() for tag in c['tags']))
    candidates = [c for c in data['capabilities'] if route is None or c['route'] == route]
    return sorted([c for c in candidates if not tokens or score(c)], key=lambda c: (-score(c), c['id']))[:max(0, limit)]

def context(data, state, query='', route=None, limit=3):
    selected = select_capabilities(data, query, route, limit)
    ids = {c['id'] for c in selected}
    return {'capabilities': selected, 'preferences': data['preferences'], 'curriculum': [c for c in data['curriculum'] if ids.intersection(c['capability_ids'])], 'state_summary': {k: state.get(k) for k in ('active_iteration', 'blender53_migration_request', 'render_delivery_policy')}, 'limits': LIMITS}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['check', 'lookup', 'context'])
    parser.add_argument('--registry', default=str(DEFAULT))
    parser.add_argument('--state', default=str(ROOT / 'catalog/current_state.json'))
    parser.add_argument('--query', default='')
    parser.add_argument('--route')
    parser.add_argument('--limit', type=int, default=3)
    parser.add_argument('--check-artifacts', action='store_true')
    args = parser.parse_args()
    try:
        data = load(args.registry)
        errors = validate(data, check_artifacts=args.check_artifacts)
        if errors:
            result = {'errors': errors, 'limits': LIMITS}
        elif args.command == 'check':
            result = {'valid': True, 'limits': LIMITS}
        elif args.command == 'lookup':
            result = {'capabilities': select_capabilities(data, args.query, args.route, args.limit), 'limits': LIMITS}
        else:
            result = context(data, load(args.state), args.query, args.route, args.limit)
    except (OSError, ValueError, TypeError) as e:
        errors = [str(e)]
        result = {'errors': errors, 'limits': LIMITS}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(bool(errors))
if __name__ == '__main__':
    raise SystemExit(main())
