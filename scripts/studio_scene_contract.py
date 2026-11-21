"""Read-only bounded scene benchmark contract (stdlib only)."""
import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import re
ROOT = Path(__file__).resolve().parents[1]
ROLES = set('face skin hair cloth fur metal iris eye_white ink transparent mouth other'.split())

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def digest(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for block in iter(lambda: f.read(1048576), b''):
            h.update(block)
    return h.hexdigest()

def number(v):
    return type(v) in (int, float) and math.isfinite(v)

def validate(p, root=ROOT, check_source=False):
    e = []
    try:
        if not isinstance(p, dict):
            raise ValueError('profile must be an object')
        if not p.get('schema_version') == 1:
            raise ValueError('schema_version must be 1')
        if not (isinstance(p['id'], str) and re.fullmatch('[a-zA-Z0-9_-]+', p['id'])):
            raise ValueError('id required')
        s = p['source']
        path = s['path']
        if not (isinstance(path, str) and '://' not in path and (Path(path).is_absolute() or re.match('^[A-Za-z]:[/\\\\]', path))):
            raise ValueError('source must be local absolute path')
        if not re.fullmatch('[0-9a-fA-F]{64}', s['sha256']):
            raise ValueError('source sha256 invalid')
        if check_source:
            if not digest(path).lower() == s['sha256'].lower():
                raise ValueError('source hash mismatch')
        r = p['runtime']
        target = (Path(root) / r).resolve()
        if not (not Path(r).is_absolute() and ':' not in r and target.is_relative_to(Path(root).resolve()) and (target.suffix == '.json') and target.is_file()):
            raise ValueError('runtime must be existing repo JSON')
        load(target)
        scene = p['scene']
        if not all((isinstance(scene[k], str) and scene[k] for k in ('name', 'camera'))):
            raise ValueError('scene names required')
        if not scene['registration'] in ('mmd_tools', 'none'):
            raise ValueError('registration invalid')
        if not (scene['expected_lens_mm'] is None or number(scene['expected_lens_mm'])):
            raise ValueError('lens invalid')
        ids = set()
        objects = set()
        roles = {}
        if not (isinstance(p['actors'], list) and p['actors']):
            raise ValueError('actors required')
        for a in p['actors']:
            if not a['id'] not in ids:
                raise ValueError('duplicate actor id')
            ids.add(a['id'])
            if not (isinstance(a['objects'], list) and a['objects']):
                raise ValueError('actor objects required')
            for obj in a['objects']:
                if not (isinstance(obj, str) and obj and (obj not in objects)):
                    raise ValueError('duplicate/invalid object membership')
                objects.add(obj)
            if not isinstance(a['materials'], dict):
                raise ValueError('material mapping required')
            for role, names in a['materials'].items():
                if not (role in ROLES and isinstance(names, list) and names):
                    raise ValueError('invalid material role')
                for name in names:
                    if not (isinstance(name, str) and name):
                        raise ValueError('invalid material name')
                    if not (name not in roles or roles[name] == role):
                        raise ValueError('conflicting material roles')
                    roles[name] = role
        switches = p['switches']
        if not isinstance(switches, dict):
            raise ValueError('switches must be object')
        fields = {'node_input': ('material', 'node', 'socket', 'expected'), 'light_energy': ('object', 'expected'), 'object_hide': ('object', 'expected'), 'modifier_enabled': ('object', 'modifier', 'expected'), 'glow_bypass': ('nodes',)}
        for key, sw in switches.items():
            if not (isinstance(key, str) and re.fullmatch('[a-zA-Z0-9_-]+', key)):
                raise ValueError('invalid switch name')
            kind = sw['kind']
            if not kind in fields:
                raise ValueError('unknown switch kind')
            if not all((k in sw for k in fields[kind])):
                raise ValueError('missing switch selector')
            if kind in ('object_hide', 'modifier_enabled'):
                if not type(sw['expected']) is bool:
                    raise ValueError('expected must be boolean')
            if kind == 'light_energy':
                if not (number(sw['expected']) and sw['expected'] >= 0):
                    raise ValueError('expected energy invalid')
            if kind == 'node_input':
                if sw.get('socket_match', 'unique') not in ('unique', 'identifier'):
                    raise ValueError('invalid socket matching mode')
                if not (type(sw['expected']) is bool or number(sw['expected']) or (isinstance(sw['expected'], list) and bool(sw['expected']) and all((number(x) for x in sw['expected'])))):
                    raise ValueError('invalid expected input')
            if kind == 'glow_bypass':
                if not (isinstance(sw['nodes'], list) and sw['nodes']):
                    raise ValueError('glow nodes required')
                for n in sw['nodes']:
                    if not (n['tree'] == 'compositor' and n['scene'] and n['node'] and (n['image_output'] == 'Image') and (n['glare_output'] == 'Glare')):
                        raise ValueError('glow outputs must be explicit')
        cases = p['cases']
        if not (isinstance(cases, list) and 1 <= len(cases) <= 32):
            raise ValueError('case count invalid')
        ids = set()
        for c in cases:
            if not (isinstance(c['id'], str) and re.fullmatch('[a-zA-Z0-9_-]+', c['id']) and (c['id'].casefold() not in ids)):
                raise ValueError('duplicate/invalid case id')
            ids.add(c['id'].casefold())
            if not type(c['frame']) is int:
                raise ValueError('frame must be integer')
            seen = set()
            for o in c['overrides']:
                key = o['switch']
                if not (key in switches and key not in seen):
                    raise ValueError('unknown/duplicate override')
                seen.add(key)
                v = o['value']
                kind = switches[key]['kind']
                if kind == 'light_energy':
                    if not (number(v) and v >= 0):
                        raise ValueError('negative energy')
                if kind == 'glow_bypass':
                    if not v is True:
                        raise ValueError('glow bypass must be true')
                if kind == 'node_input':
                    expected = switches[key]['expected']
                    if not (type(v) is bool if type(expected) is bool else number(v) if number(expected) else isinstance(v, list) and len(v) == len(expected) and all((number(x) for x in v))):
                        raise ValueError('input shape/type mismatch')
                elif kind in ('object_hide', 'modifier_enabled'):
                    if not type(v) is bool:
                        raise ValueError('override must be boolean')
        r = p['render']
        for k, lo, hi in [('width', 64, 4096), ('height', 64, 4096), ('samples', 1, 512)]:
            if not (type(r[k]) is int and lo <= r[k] <= hi):
                raise ValueError('render bounds invalid')
        if not (r['dof'] == 'source' or type(r['dof']) is bool):
            raise ValueError('dof invalid')
        if not r['motion_blur'] is False:
            raise ValueError('motion blur forbidden')
        if not r.get('format', 'PNG') == 'PNG':
            raise ValueError('only PNG supported')
        if not all((not p.get(k, False) and (not r.get(k, False)) for k in ('animation', 'save', 'physics'))):
            raise ValueError('temporal/write flags forbidden')
        if not (isinstance(p['limits'], list) and p['limits'] and all((isinstance(x, str) and x.strip() for x in p['limits']))):
            raise ValueError('limits required')
    except (AssertionError, KeyError, TypeError, ValueError, OSError, AttributeError) as ex:
        e.append(str(ex) or 'malformed profile')
    return e

def equal(a, b):
    if number(a) and number(b):
        # Blender RNA stores many controls as float32. Absolute-only tolerance
        # rejects correctly assigned light energies (e.g. 677.6 -> 677.599976).
        return math.isclose(a, b, rel_tol=1e-7, abs_tol=1e-6)
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all((equal(x, y) for x, y in zip(a, b)))
    return type(a) is type(b) and a == b

def bind(p, inventory):
    errors = validate(p)
    actors = copy.deepcopy(p.get('actors', [])) if isinstance(p, dict) else []
    if errors:
        return {'passed': False, 'errors': errors, 'actors': actors}
    try:

        def need(ok, msg):
            if not ok:
                errors.append(msg)
        need(inventory['source']['sha256'].lower() == p['source']['sha256'].lower(), 'source hash mismatch')
        s = inventory['scene']
        expected = p['scene']
        need(s['name'] == expected['name'] and s['camera'] == expected['camera'], 'scene/camera mismatch')
        if expected['expected_lens_mm'] is not None:
            need(number(s['lens_mm']) and abs(s['lens_mm'] - expected['expected_lens_mm']) <= 0.001, 'lens mismatch')
        objects = {o['name']: o for o in inventory['objects']}
        mats = {m['name']: m for m in inventory['materials']}
        for a in p['actors']:
            used = set()
            rig = a.get('armature')
            if rig is not None:
                need(isinstance(rig, str) and objects.get(rig, {}).get('type') == 'ARMATURE', 'missing declared armature')
            for name in a['objects']:
                o = objects.get(name, {})
                need(o.get('scene_local', True) is not False, 'actor outside scene: ' + name)
                need(o.get('type') == 'MESH', 'missing/non-mesh actor object: ' + name)
                used.update(o.get('materials', []))
                if rig is not None:
                    need(rig in o.get('armature_targets', []), 'mesh not bound to declared armature: ' + name)
            for names in a['materials'].values():
                for name in names:
                    need(name in mats and name in used, 'material not used by actor: ' + name)
        for key, sw in p['switches'].items():
            kind = sw['kind']
            if kind == 'node_input':
                allowed = {name for a in p['actors'] for name in a['objects']}
                affected = [o['name'] for o in inventory['objects'] if sw['material'] in o.get('materials', [])]
                need(all((name in allowed for name in affected)), 'material affects undeclared objects: ' + repr(affected))
                nodes = mats.get(sw['material'], {}).get('nodes', [])
                node = next((n for n in nodes if n['name'] == sw['node']), {})
                matches = [x for x in node.get('inputs', []) if
                           (sw['socket'] == x['identifier'] if sw.get('socket_match') == 'identifier'
                            else sw['socket'] in (x['name'], x['identifier']))]
                socket = matches[0] if len(matches) == 1 else None
                need(socket is not None, 'missing node/socket: ' + key)
                if socket:
                    need(not socket['linked'] and (not socket.get('driven', False)) and (not socket.get('animated', False)) and equal(socket['value'], sw['expected']), 'linked/expected mismatch: ' + key)
            elif kind == 'glow_bypass':
                for sel in sw['nodes']:
                    tree = next((t for t in inventory['compositor'] if t['scene'] == sel['scene']), {})
                    need(all((user == sel['scene'] for user in tree.get('tree_users', []))), 'shared compositor tree: ' + key)
                    node = next((n for n in tree.get('nodes', []) if n['name'] == sel['node']), {})
                    need(node.get('type') in ('GLARE', 'CompositorNodeGlare') and all((sel[k] in node.get('outputs', []) for k in ('image_output', 'glare_output'))), 'invalid glare selector: ' + key)
            else:
                obj = objects.get(sw['object'], {})
                need(bool(obj), 'missing switch object: ' + key)
                if kind == 'light_energy':
                    need(obj.get('type') == 'LIGHT', 'energy selector is not light: ' + key)
                if kind == 'modifier_enabled':
                    need(sw['modifier'] in obj.get('modifiers', []), 'missing modifier: ' + key)
                state_key = {'light_energy': 'energy', 'object_hide': 'hide_render', 'modifier_enabled': 'modifier_states'}[kind]
                protection = obj.get('control_protection', {})
                control = protection.get('modifiers', {}).get(sw['modifier'], {}) if kind == 'modifier_enabled' else protection.get(state_key, {})
                need(not control.get('driven', False) and (not control.get('animated', False)), 'animated/driven object control: ' + key)
                if state_key in obj:
                    actual = obj[state_key].get(sw['modifier']) if kind == 'modifier_enabled' else obj[state_key]
                    need(equal(actual, sw['expected']), 'object expected mismatch: ' + key)
    except (KeyError, TypeError, ValueError, AttributeError) as ex:
        errors.append('malformed inventory: ' + str(ex))
    return {'passed': not errors, 'errors': errors, 'actors': actors}

def plan(p):
    errors = validate(p)
    if errors:
        raise ValueError('; '.join(errors))
    return copy.deepcopy({'schema_version': 1, 'id': p['id'], 'source': p['source'], 'runtime': p['runtime'], 'scene': p['scene'], 'actors': p['actors'], 'switches': p['switches'], 'cases': p['cases'], 'render': p['render'], 'animation': False, 'save': False, 'physics': False})

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('check', 'plan', 'bind'))
    parser.add_argument('--profile', required=True)
    parser.add_argument('--inventory')
    parser.add_argument('--check-source', action='store_true')
    args = parser.parse_args()
    try:
        p = load(args.profile)
        if args.command == 'check':
            errors = validate(p, check_source=args.check_source)
            result = {'passed': not errors, 'errors': errors}
        elif args.command == 'plan':
            result = plan(p)
        else:
            result = bind(p, load(args.inventory))
    except (OSError, ValueError, TypeError) as ex:
        result = {'passed': False, 'errors': [str(ex)]}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return int(result.get('passed', True) is False)
if __name__ == '__main__':
    raise SystemExit(main())
