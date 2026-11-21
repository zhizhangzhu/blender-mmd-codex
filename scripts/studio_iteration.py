"""Explicit, bounded reference experiments; no visual judgments are inferred."""
import argparse
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from scripts import reference_study as study, studio_scene_contract as contract, studio_bench
ROOT = Path(__file__).resolve().parents[1]
load = study.load
sha256 = study.digest

def write(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)

def require(test, message):
    if not test:
        raise ValueError(message)

def compile_plan(plan, reference, profile):
    require(plan.get('schema_version') == 1 and re.fullmatch(r'[A-Za-z0-9_-]+', plan['id']), 'invalid plan')
    require(isinstance(plan['title'], str) and bool(plan['title'].strip()) and all(isinstance(plan[k], list) and all(isinstance(x, str) and x.strip() for x in plan[k]) for k in ('preserve', 'limits')), 'missing scope')
    observations = {x['id']: x for x in reference['observations']}
    def seen(item):
        return item.get('observation_ids') and all(observations.get(x, {}).get('seen') is True for x in item['observation_ids'])
    targets = {x['id']: x for x in reference['targets']}
    hypotheses = {x['id']: x for x in reference['hypotheses']}
    chosen = plan['target_ids']
    require(chosen and len(set(chosen)) == len(chosen) and all(x in targets and seen(targets[x]) for x in chosen), 'unknown or unseen target')
    baseline = next((x for x in profile['cases'] if x['id'] == plan['baseline_case']), None)
    require(baseline is not None and baseline['overrides'] == [], 'baseline must exist without overrides')
    result = copy.deepcopy(profile)
    result['cases'] = [copy.deepcopy(baseline)]
    prior = {baseline['id']: baseline}
    require(1 <= len(plan['experiments']) <= 2, 'one or two experiments required')
    for exp in plan['experiments']:
        key = exp['id']
        require(isinstance(key, str) and re.fullmatch(r'[A-Za-z0-9_-]+', key) and key.casefold() not in {x.casefold() for x in prior}, 'invalid/duplicate case')
        require(exp['compare_to'] in prior, 'compare_to must precede experiment')
        require(exp['hypothesis_id'] in hypotheses and seen(hypotheses[exp['hypothesis_id']]), 'unknown or unseen hypothesis')
        require(exp['target_ids'] and len(set(exp['target_ids'])) == len(exp['target_ids']) and set(exp['target_ids']) <= set(chosen), 'unknown experiment target')
        require(exp['prediction'] and exp['change_kind'] in ('ablation', 'design_option') and exp['overrides'], 'explicit prediction and changes required')
        old = {x['switch']: x['value'] for x in prior[exp['compare_to']]['overrides']}
        new = {x['switch']: x['value'] for x in exp['overrides']}
        changes = sum(old.get(k) != new.get(k) for k in old.keys() | new.keys())
        require(changes > 0 and (exp['change_kind'] != 'ablation' or changes == 1 or exp.get('change_group')), 'ablation needs one logical change or named group')
        case = dict(id=key, frame=baseline['frame'], overrides=copy.deepcopy(exp['overrides']))
        result['cases'].append(case)
        prior[key] = case
    return result

def prepare(plan_path, output, root=ROOT):
    plan_path, output, root = Path(plan_path), Path(output), Path(root)
    plan = load(plan_path)
    inputs = {}
    for name in ('study', 'profile'):
        path = study.local_path(plan[name]['path'], root)
        require(sha256(path) == plan[name]['sha256'], name + ' hash mismatch')
        inputs[name] = load(path)
    require(not study.validate(inputs['study'], root=root, check_artifacts=True), 'invalid reference study')
    require(not contract.validate(inputs['profile'], root=root, check_source=True), 'invalid bench profile')
    compiled = compile_plan(plan, inputs['study'], inputs['profile'])
    require(not contract.validate(compiled, root=root, check_source=True), 'invalid compiled profile')
    output.mkdir(parents=True, exist_ok=False)
    (output / 'inputs').mkdir()
    pins = {}
    for name, data in dict(inputs, plan=plan).items():
        path = output / 'inputs' / (name + '.json')
        write(path, data)
        pins[name] = {'path': str(path.resolve()), 'sha256': sha256(path), 'origin': str(plan_path.resolve()) if name == 'plan' else plan[name]['path']}
    write(output / 'compiled-profile.json', compiled)
    manifest = dict(schema_version=1, id=plan['id'], created_at=datetime.now(timezone.utc).isoformat(), inputs=pins, compiled_sha256=sha256(output / 'compiled-profile.json'), plan_sha256=pins['plan']['sha256'], source=compiled['source'], sourcecode_sha256=sha256(__file__))
    manifest['code_pins'] = {}
    for key, path in [('worker', Path(studio_bench.WORKER)), ('contract', Path(contract.__file__)), ('runtime', root / compiled['runtime'])]:
        manifest['code_pins'][key] = {'path': str(path.resolve()), 'sha256': sha256(path)}
    write(output / 'manifest.json', manifest)
    return manifest

def check(directory, root=ROOT, check_run=True):
    d = Path(directory)
    try:
        m = load(d / 'manifest.json')
        for name, pin in m['inputs'].items():
            require(sha256(d / 'inputs' / (name + '.json')) == pin['sha256'], 'snapshot changed: ' + name)
        require(sha256(d / 'compiled-profile.json') == m['compiled_sha256'], 'compiled profile changed')
        p, s, original = [load(d / 'inputs' / (n + '.json')) for n in ('plan', 'study', 'profile')]
        c = load(d / 'compiled-profile.json')
        require(compile_plan(p, s, original) == c, 'compiled semantics mismatch')
        require(not study.validate(s, root=root, check_artifacts=True), 'reference artifacts changed')
        if not (d / 'run-link.json').exists():
            for pin in m['code_pins'].values():
                require(sha256(pin['path']) == pin['sha256'], 'execution code changed')
        require(m['source'] == c['source'] and m['plan_sha256'] == m['inputs']['plan']['sha256'], 'manifest mismatch')
        require(sha256(c['source']['path']) == c['source']['sha256'], 'source changed')
        if check_run and (d / 'run-link.json').exists():
            link = load(d / 'run-link.json')
            require(sha256(d / 'run' / 'report.json') == link['sha256'], 'run report changed')
            report = load(d / 'run' / 'report.json')
            require(report.get('profile_sha256') == m['compiled_sha256'] and report.get('source') == c['source'] and report.get('source_unchanged') is True, 'worker input mismatch')
            require(sha256(d / 'run' / 'launch.json') == link['launch_sha256'], 'launch changed')
            launch = load(d / 'run' / 'launch.json')
            for key, field in [('worker', 'worker_sha256'), ('contract', 'contract_sha256'), ('runtime', 'runtime_config_sha256')]:
                require(report.get(field) == m['code_pins'][key]['sha256'], 'run code mismatch')
            if report.get('passed') is True:
                require(launch.get('passed') is True and launch.get('returncode') == 0 and launch.get('source_sha256_after') == c['source']['sha256'], 'launch unsuccessful')
                for case in report['cases']:
                    require(all(case.get(key) == report['cases'][0].get(key) and key in case for key in ('camera', 'effective_render', 'color')), 'comparison settings differ')
                    require(case['camera'].get('name') == c['scene']['camera'], 'camera mismatch')
                    image = Path(case['path']).resolve()
                    require(image.is_relative_to((d / 'run').resolve()) and sha256(image) == case['sha256'] and case.get('passed') is True, 'case image invalid')
            require(launch['profile_sha256'] == m['compiled_sha256'] and launch['source_sha256_before'] == c['source']['sha256'], 'run input mismatch')
            require([{k: x[k] for k in ('id', 'frame', 'overrides')} for x in report['cases']] == c['cases'], 'run cases mismatch')
        for artifact, linkname in [('review.json', 'review-link.json'), ('user-feedback.json', 'user-feedback-link.json'), ('lesson.json', 'close-link.json')]:
            if (d / artifact).exists() or (d / linkname).exists():
                require(sha256(d / artifact) == load(d / linkname)['sha256'], 'frozen artifact changed: ' + artifact)
        if (d / 'user-feedback-link.json').exists():
            pin = load(d / 'user-feedback-link.json')['provenance']
            require(sha256(pin['path']) == pin['sha256'], 'feedback provenance changed')
        if (d / 'close-link.json').exists():
            from scripts.studio_review_board import validate_board
            pin = load(d / 'close-link.json')['board']
            require(sha256(d / 'board/manifest.json') == pin['sha256'] and not validate_board(d), 'closed board changed')
        return []
    except (ValueError, KeyError, TypeError, OSError) as exc:
        return [str(exc)]

def run(directory, execute=False, timeout=600):
    d = Path(directory)
    require(not check(d), 'iteration check failed')
    c = load(d / 'compiled-profile.json')
    require(not (d / 'run').exists(), 'run already exists')
    result = studio_bench.dispatch(load(ROOT / c['runtime']), 'render', d / 'compiled-profile.json', c['source']['path'], d / 'run', execute=execute, timeout=timeout)
    if execute and (d / 'run' / 'report.json').is_file():
        write(d / 'run-link.json', {'path': str((d / 'run' / 'report.json').resolve()), 'sha256': sha256(d / 'run' / 'report.json'), 'launch_sha256': sha256(d / 'run' / 'launch.json')})
    return result

def validate_review(directory, review_path):
    d = Path(directory)
    require(not check(d) and (d / 'run-link.json').exists(), 'valid pinned run required')
    require(load(d / 'run' / 'report.json')['passed'] is True and load(d / 'run' / 'launch.json')['passed'] is True, 'passing run required')
    r, p = load(review_path), load(d / 'inputs' / 'plan.json')
    require(r.get('schema_version') == 1 and r['iteration_id'] == p['id'] and r['run_report_sha256'] == load(d / 'run-link.json')['sha256'], 'review pin mismatch')
    kind = r['reviewer']['kind']
    require(kind in ('ai', 'user') and r['reviewer']['identity'] and r['reviewer']['scope'], 'reviewer required')
    require(type(r['user_approval']) is bool and not (kind == 'ai' and r['user_approval']), 'AI cannot approve artwork')
    if r['user_approval']:
        require(sha256(r['user_feedback_provenance']) == r['user_feedback_provenance_sha256'], 'feedback provenance mismatch')
    cases = {x['id'] for x in load(d / 'compiled-profile.json')['cases']}
    seen = r['seen_cases']
    require(seen and len(set(seen)) == len(seen) and set(seen) <= cases, 'invalid seen cases')
    require(r['selection'] is None or (r['selection'] in seen and p['baseline_case'] in seen), 'selection requires observed baseline')
    require(len(r['targets']) == len(p['target_ids']) and {x['target_id'] for x in r['targets']} == set(p['target_ids']), 'review targets mismatch')
    require(not any(x['verdict'] == 'improved' for x in r['targets']) or cases <= set(seen), 'improvement requires all candidate cases seen')
    for target in r['targets']:
        require(target['verdict'] in ('improved', 'unchanged', 'regressed', 'inconclusive') and target['observations'] and all(isinstance(x, str) and x.strip() for x in target['observations']) and isinstance(target['tradeoffs'], list), 'concrete target observations required')
    outcomes = r['hypothesis_outcomes']
    expected = {e['id']: e['hypothesis_id'] for e in p['experiments']}
    require(len(outcomes) == len(expected) and {x['experiment_id'] for x in outcomes} == set(expected), 'each experiment needs hypothesis outcome')
    for outcome in outcomes:
        require(outcome['hypothesis_id'] == expected[outcome['experiment_id']] and outcome['outcome'] in ('supported', 'rejected', 'inconclusive') and isinstance(outcome['reason'], str) and outcome['reason'].strip(), 'invalid hypothesis outcome')
        require(outcome['outcome'] == 'inconclusive' or (outcome['experiment_id'] in seen and p['baseline_case'] in seen), 'hypothesis outcome requires seen comparison')
    require(r['reasons'] and r['next_action'], 'review reasons required')
    return r

def record_review(directory, review_path):
    r = validate_review(directory, review_path)
    require(r['reviewer']['kind'] == 'ai' and r['user_approval'] is False, 'use user-feedback for user review')
    d = Path(directory)
    require(not (d / 'review-link.json').exists(), 'review already frozen')
    write(d / 'review.json', r)
    write(d / 'review-link.json', {'path': str((d / 'review.json').resolve()), 'sha256': sha256(d / 'review.json')})
    return r

def record_user_feedback(directory, feedback_path):
    """Freeze a separate provenance-backed user record; never rewrite a lesson."""
    d = Path(directory)
    r = validate_review(d, feedback_path)
    require(r['reviewer']['kind'] == 'user', 'user feedback requires user reviewer')
    provenance = Path(r['user_feedback_provenance'])
    require(provenance.is_absolute() and provenance.is_file() and sha256(provenance) == r['user_feedback_provenance_sha256'], 'user feedback requires provenance SHA')
    require(not (d / 'user-feedback-link.json').exists(), 'feedback already frozen')
    write(d / 'user-feedback.json', r)
    write(d / 'user-feedback-link.json', {'path': str((d / 'user-feedback.json').resolve()), 'sha256': sha256(d / 'user-feedback.json'), 'provenance': {'path': str(provenance), 'sha256': sha256(provenance)}})
    return r


def close(directory):
    d = Path(directory)
    require(not check(d), 'iteration check failed')
    require(sha256(d / 'review.json') == load(d / 'review-link.json')['sha256'], 'frozen review changed')
    r = load(d / 'review.json')
    validate_review(d, d / 'review.json')
    from scripts.studio_review_board import validate_board
    require(not validate_board(d), 'valid review board required')
    board_pin = {'path': str((d / 'board/manifest.json').resolve()), 'sha256': sha256(d / 'board/manifest.json')}
    p = load(d / 'inputs' / 'plan.json')
    lesson = dict(schema_version=1, id=p['id'], title=p['title'], route='render', study_id=load(d / 'inputs' / 'study.json')['id'], scope=p['preserve'], plan_sha256=sha256(d / 'inputs' / 'plan.json'), run=load(d / 'run-link.json'), review={'path': str((d / 'review.json').resolve()), 'sha256': sha256(d / 'review.json')}, source=load(d / 'manifest.json')['source'], findings=r['targets'], selection=r['selection'], next_action=r['next_action'], user_approval=r['user_approval'], transfer_level='single_case', references=[p['study']['path']], limits=p['limits'])
    lesson['board'] = board_pin
    lesson['hypothesis_outcomes'] = r['hypothesis_outcomes']
    if (d / 'user-feedback-link.json').exists():
        lesson['user_feedback'] = load(d / 'user-feedback-link.json')
        lesson['user_approval'] = load(d / 'user-feedback.json')['user_approval']
    write(d / 'lesson.json', lesson)
    write(d / 'close-link.json', {'path': str((d / 'lesson.json').resolve()), 'sha256': sha256(d / 'lesson.json'), 'board': board_pin})
    return lesson

def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('command', choices=['prepare', 'check', 'run', 'review', 'user-feedback', 'close'])
    for flag in ('plan', 'output', 'iteration', 'review'):
        parser.add_argument('--' + flag)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--timeout', type=int, default=600)
    a = parser.parse_args(argv)
    try:
        result = prepare(a.plan, a.output) if a.command == 'prepare' else check(a.iteration) if a.command == 'check' else run(a.iteration, a.execute, a.timeout) if a.command == 'run' else record_review(a.iteration, a.review) if a.command == 'review' else record_user_feedback(a.iteration, a.review) if a.command == 'user-feedback' else close(a.iteration)
        print(json.dumps(result, ensure_ascii=False))
        return int(bool(result) if a.command == 'check' else isinstance(result, dict) and result.get('passed') is False and a.execute)
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'errors': [str(exc)]}))
        return 1

if __name__ == '__main__':
    raise SystemExit(main())

