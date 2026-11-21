"""Planning-only model recommendations and bounded task packets (stdlib only)."""
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys
import uuid

ROOT = Path(__file__).resolve().parents[1]
POLICY = ROOT / 'catalog/model_policy.json'


def validate_policy(data):
    errors = []
    if not isinstance(data, dict):
        return ['policy must be an object']
    if data.get('schema_version') != 1:
        errors.append('schema_version must be 1')
    roles = data.get('roles', {})
    for role in ('supervisor', 'executor'):
        config = roles.get(role) if isinstance(roles, dict) else None
        efforts = ('high', 'xhigh', 'max', 'ultra') if role == 'supervisor' else ('low',)
        if not isinstance(config, dict) or not isinstance(config.get('model'), str) or not config['model'].strip() or config.get('reasoning_effort') not in efforts:
            errors.append('invalid role: ' + role)
    kinds = data.get('task_kinds')
    if not isinstance(kinds, dict) or not kinds or any(not isinstance(k, str) or not k or v not in ('supervisor', 'executor') for k, v in kinds.items()):
        errors.append('invalid task_kinds')
    escalation = data.get('escalation', {})
    if not isinstance(escalation, dict) or type(escalation.get('max_attempts')) is not int or escalation.get('max_attempts', 0) < 1:
        errors.append('invalid max_attempts')
    for name, value in [('conditions', escalation.get('conditions') if isinstance(escalation, dict) else None), ('principles', data.get('principles'))]:
        if not isinstance(value, list) or not value or any(not isinstance(x, str) or not x.strip() for x in value):
            errors.append('invalid ' + name)
    return errors


def load_policy(path=POLICY):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    errors = validate_policy(data)
    if errors:
        raise ValueError('; '.join(errors))
    return data


def recommend(policy, kind, uncertainty='bounded', attempts=0):
    errors = validate_policy(policy)
    if errors:
        raise ValueError('; '.join(errors))
    if kind not in policy['task_kinds']:
        raise ValueError('unknown kind: ' + str(kind))
    if uncertainty not in ('bounded', 'exploratory') or type(attempts) is not int or attempts < 0:
        raise ValueError('invalid uncertainty or attempts')
    role = 'supervisor' if uncertainty != 'bounded' or attempts >= policy['escalation']['max_attempts'] else policy['task_kinds'][kind]
    return dict(role=role, **policy['roles'][role])


def _reference(value, root):
    if not isinstance(value, str) or not value or '\\' in value or ':' in value:
        return False
    path = PurePosixPath(value)
    return not path.is_absolute() and '..' not in path.parts and (root / value).resolve().is_relative_to(root.resolve()) and (root / value).is_file()


def validate_packet(packet, root=ROOT, policy=None):
    if not isinstance(packet, dict):
        return ['packet must be an object']
    errors = []
    try:
        expected = recommend(load_policy() if policy is None else policy, packet.get('kind'), packet.get('uncertainty'), packet.get('attempts'))
        if packet.get('assignment') != expected:
            errors.append('assignment does not match policy recommendation')
    except (ValueError, OSError, TypeError, KeyError) as exc:
        errors.append('invalid recommendation: ' + str(exc))
    if packet.get('schema_version') != 1:
        errors.append('schema_version must be 1')
    for key in ('id', 'title', 'kind'):
        if not isinstance(packet.get(key), str) or not packet[key].strip():
            errors.append('invalid ' + key)
    if packet.get('uncertainty') not in ('bounded', 'exploratory') or type(packet.get('attempts')) is not int or packet.get('attempts', -1) < 0:
        errors.append('invalid uncertainty or attempts')
    for key in ('inputs', 'allowed_paths', 'deliverables', 'acceptance', 'context_refs', 'escalate_if'):
        value = packet.get(key)
        if not isinstance(value, list) or any(not isinstance(x, str) or not x.strip() for x in value) or (key != 'context_refs' and not value):
            errors.append('invalid ' + key)
    for ref in packet.get('context_refs', []) if isinstance(packet.get('context_refs'), list) else []:
        if not _reference(ref, Path(root)):
            errors.append('invalid context reference: ' + str(ref))
    assignment = packet.get('assignment', {})
    if not isinstance(assignment, dict) or assignment.get('role') not in ('supervisor', 'executor') or not isinstance(assignment.get('model'), str) or not assignment.get('model', '').strip() or assignment.get('reasoning_effort') not in (('high', 'xhigh', 'max', 'ultra') if assignment.get('role') == 'supervisor' else ('low',)):
        errors.append('invalid assignment')
    execution = packet.get('execution', {})
    if not isinstance(execution, dict) or execution.get('status') not in ('not_dispatched', 'dispatched', 'completed', 'failed'):
        errors.append('invalid execution')
    elif execution['status'] in ('dispatched', 'completed') and (not execution.get('actual_model') or not execution.get('actual_reasoning_effort')):
        errors.append('actual execution model and effort required')
    if isinstance(execution, dict):
        if execution.get('status') == 'not_dispatched' and (any(execution.get(k) is not None for k in ('actual_model', 'actual_reasoning_effort', 'elapsed_seconds', 'cost')) or execution.get('attempts') != 0):
            errors.append('not_dispatched requires empty execution evidence')
        for key in ('elapsed_seconds', 'cost'):
            value = execution.get(key)
            if value is not None and (type(value) not in (int, float) or not __import__('math').isfinite(value) or value < 0):
                errors.append('invalid execution ' + key)
    review = packet.get('review', {})
    if not isinstance(review, dict) or type(review.get('user_approval')) is not bool:
        errors.append('invalid review')
    elif review['user_approval'] and not _reference(review.get('user_feedback_provenance'), Path(root)):
        errors.append('user approval requires feedback provenance')
    return errors


def build_packet(policy, title, kind, inputs, allowed_paths, deliverables, acceptance, context_refs=(), uncertainty='bounded', attempts=0):
    packet = dict(schema_version=1, id=re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-') or str(uuid.uuid4()), title=title, kind=kind, assignment=recommend(policy, kind, uncertainty, attempts), uncertainty=uncertainty, attempts=attempts, inputs=list(inputs), allowed_paths=list(allowed_paths), deliverables=list(deliverables), acceptance=list(acceptance), context_refs=list(context_refs), escalate_if=list(policy['escalation']['conditions']), execution=dict(status='not_dispatched', actual_model=None, actual_reasoning_effort=None, elapsed_seconds=None, cost=None, attempts=0), review=dict(technical='untested', art='pending', user_approval=False), limits='Recommendation only; not dispatched. Model availability is unverified; this does not switch the current session. Ownership paths are lexical scope only; no production changes are authorized implicitly.')
    errors = validate_packet(packet, policy=policy)
    if errors:
        raise ValueError('; '.join(errors))
    return packet


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--policy', default=str(POLICY))
    sub = parser.add_subparsers(dest='command', required=True)
    for command in ('recommend', 'packet'):
        p = sub.add_parser(command)
        p.add_argument('--kind', required=True)
        p.add_argument('--uncertainty', default='bounded', choices=('bounded', 'exploratory'))
        p.add_argument('--attempts', type=int, default=0)
        if command == 'packet':
            p.add_argument('--title', required=True)
            for flag in ('input', 'allow', 'deliverable', 'accept', 'context-ref'):
                p.add_argument('--' + flag, action='append', default=[])
            p.add_argument('--output')
    p = sub.add_parser('check')
    p.add_argument('--packet', required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'check':
            errors = validate_packet(json.loads(Path(args.packet).read_text(encoding='utf-8-sig')), policy=load_policy(args.policy))
            result = dict(valid=not errors, errors=errors)
        else:
            policy = load_policy(args.policy)
            result = recommend(policy, args.kind, args.uncertainty, args.attempts) if args.command == 'recommend' else build_packet(policy, args.title, args.kind, args.input, args.allow, args.deliverable, args.accept, args.context_ref, args.uncertainty, args.attempts)
        encoded = json.dumps(result, ensure_ascii=False, indent=2)
        if getattr(args, 'output', None):
            with Path(args.output).open('x', encoding='utf-8') as stream:
                stream.write(encoded + '\n')
        else:
            print(encoded)
        return 1 if args.command == 'check' and errors else 0
    except (ValueError, OSError, TypeError, KeyError) as exc:
        print(json.dumps({'errors': [str(exc)]}, ensure_ascii=False), file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
