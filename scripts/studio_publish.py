"""Explicit isolated candidate publication and independent reopen launcher (stdlib)."""
import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time
from scripts import studio_iteration as iteration
ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / 'scripts/studio_publish_worker.py'
SAFE_KINDS = {'node_input', 'light_energy', 'glow_bypass'}
load = iteration.load
sha256 = iteration.sha256
require = iteration.require

def encoded(value):
    return json.dumps(value, ensure_ascii=False, indent=2).encode('utf-8')

def fingerprint(value):
    return hashlib.sha256(encoded(value)).hexdigest()

def pin(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': sha256(path)}

def verify(value):
    require(Path(value['path']).is_absolute() and sha256(value['path']) == value['sha256'], 'input pin changed: ' + str(value['path']))

def plan(directory, case_id, output, mode='publish', publish_report=None):
    d, output = Path(directory).resolve(), Path(output).resolve()
    require(mode in ('publish', 'reopen'), 'invalid publication mode')
    require(not iteration.check(d), 'closed iteration integrity check failed')
    require((d / 'close-link.json').is_file(), 'closed iteration required')
    lesson = load(d / 'lesson.json')
    require(lesson['selection'] == case_id, 'only selected case may be published')
    profile = copy.deepcopy(load(d / 'compiled-profile.json'))
    original = profile['source']
    verify(original)
    require(not output.exists(), 'new output directory required')
    source_path = Path(original['path']).resolve()
    require(output != source_path.parent and not source_path.is_relative_to(output) and not output.is_relative_to(ROOT.resolve()), 'output conflicts with protected source/repository')
    require(not d.is_relative_to(output) and not output.is_relative_to(d), 'output conflicts with frozen iteration')
    case = next((x for x in profile['cases'] if x['id'] == case_id), None)
    require(case is not None, 'unknown case')
    switches = profile['switches']
    require(all(switches[x['switch']]['kind'] in SAFE_KINDS for x in case['overrides']), 'unsupported publication override kind')
    profile['cases'] = [case]
    profile['render'].update(width=1920, height=1080, samples=64, dof='source', motion_blur=False)
    runtime = pin(ROOT / profile['runtime'])
    pins = {'worker': pin(WORKER), 'benchworker': pin(ROOT / 'scripts/studio_scene_worker.py'), 'contract': pin(ROOT / 'scripts/studio_scene_contract.py')}
    request = {'schema_version': 1, 'mode': mode, 'iteration': {'path': str(d), 'manifest_sha256': sha256(d / 'manifest.json'), 'lesson_sha256': sha256(d / 'lesson.json')}, 'case_id': case_id, 'profile': {'path': str(output / 'publish-profile.json'), 'sha256': fingerprint(profile)}, 'expected_source': original, 'runtime': runtime, 'pins': pins, 'publish_report': None, 'reopen_tolerance': {'max_abs': .005, 'mean_abs': .0001}}
    if mode == 'reopen':
        require(publish_report is not None, 'publish report required for reopen')
        report_pin = pin(publish_report)
        report = load(publish_report)
        previous_request_path = Path(publish_report).resolve().parent / 'request.json'
        previous = load(previous_request_path)
        previous_launch = load(Path(publish_report).resolve().parent / 'launch.json')
        require(previous_launch.get('passed') is True and previous_launch.get('returncode') == 0 and previous_launch['report']['sha256'] == report_pin['sha256'] and previous_launch['request']['sha256'] == sha256(previous_request_path), 'publish launch provenance mismatch')
        require(report['passed'] is True and report['mode'] == 'publish' and report['case_id'] == case_id, 'successful selected publish required')
        require(sha256(previous_request_path) == report['request_sha256'] and previous['iteration'] == request['iteration'] and previous['profile']['sha256'] == request['profile']['sha256'], 'publish provenance mismatch')
        require(previous['expected_source'] == original and previous['runtime'] == runtime and previous['pins'] == pins, 'publish input mismatch')
        verify(previous['profile'])
        verify(report['candidate'])
        require(Path(report['candidate']['path']).resolve().parent == Path(publish_report).resolve().parent, 'candidate outside publish directory')
        require(report['source'] == original, 'published source mismatch')
        require(output != Path(report['candidate']['path']).resolve().parent and not Path(report['candidate']['path']).resolve().is_relative_to(output), 'output conflicts with candidate')
        request['expected_source'] = report['candidate']
        request['publish_report'] = report_pin
    else:
        require(publish_report is None, 'publish report is only accepted for reopen')
    runtime_data = load(runtime['path'])
    args = [runtime_data['executable'], '--background', '--factory-startup', '--disable-autoexec', '--python-exit-code', '1', '--python', str(WORKER.resolve()), '--', '--request', str(output / 'request.json'), '--output', str(output)]
    return {'request': request, 'profile': profile, 'command': args, 'output': str(output), 'passed': False, 'execution': 'not_dispatched', 'limits': 'Candidate copy only; formal still differs from frozen benchmark settings; no artwork approval or video'}

def dispatch(directory, case_id, output, mode='publish', publish_report=None, execute=False, timeout=1800):
    require(type(timeout) in (int, float) and math.isfinite(timeout) and 1 <= timeout <= 3600, 'timeout must be finite in 1..3600')
    prepared = plan(directory, case_id, output, mode, publish_report)
    if not execute:
        return prepared
    request = prepared['request']
    runtime = load(request['runtime']['path'])
    for key in ('executable', 'user_config', 'user_scripts'):
        path = Path(runtime[key])
        require(path.is_absolute() and (path.is_file() if key == 'executable' else path.is_dir()), 'invalid isolated runtime path: ' + key)
    env = os.environ.copy()
    env.update(BLENDER_USER_CONFIG=runtime['user_config'], BLENDER_USER_SCRIPTS=runtime['user_scripts'])
    out = Path(prepared['output'])
    out.mkdir(parents=True, exist_ok=False)
    (out / 'publish-profile.json').write_bytes(encoded(prepared['profile']))
    (out / 'request.json').write_bytes(encoded(request))
    request_pin = pin(out / 'request.json')
    launch = {'mode': mode, 'case_id': case_id, 'command': prepared['command'], 'request': request_pin, 'source_sha256_before': sha256(request['expected_source']['path']), 'execution': 'dispatched', 'passed': False, 'returncode': None, 'timeout': False}
    start = time.monotonic()
    stdout = stderr = ''
    try:
        result = subprocess.run(prepared['command'], shell=False, capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, timeout=timeout)
        stdout, stderr = result.stdout, result.stderr
        launch['returncode'] = result.returncode
        report = load(out / ('publish-report.json' if mode == 'publish' else 'reopen-report.json'))
        require(result.returncode == 0 and report.get('passed') is True, 'worker publication failed')
        require(report['mode'] == mode and report['case_id'] == case_id and report['request_sha256'] == request_pin['sha256'] and report['source'] == request['expected_source'], 'worker report provenance mismatch')
        require(all(report.get(key) == request[key] for key in ('profile', 'runtime', 'pins', 'reopen_tolerance')), 'worker report input pins mismatch')
        for key in ('image', 'candidate'):
            if key == 'candidate' and mode == 'reopen':
                continue
            verify(report[key])
            require(Path(report[key]['path']).resolve().parent == out, 'worker artifact outside output')
        launch['report'] = pin(out / ('publish-report.json' if mode == 'publish' else 'reopen-report.json'))
        launch['passed'] = True
    except subprocess.TimeoutExpired as exc:
        stdout, stderr = exc.stdout or '', exc.stderr or ''
        launch.update(timeout=True, error='publication timed out')
    except (ValueError, KeyError, TypeError, OSError) as exc:
        launch['error'] = str(exc)
    finally:
        try:
            for item in [request_pin, request['profile'], request['runtime'], request['expected_source'], prepared['profile']['source'], *request['pins'].values()]:
                verify(item)
            if request['publish_report']:
                verify(request['publish_report'])
            launch['source_sha256_after'] = sha256(request['expected_source']['path'])
        except (ValueError, OSError) as exc:
            launch.update(passed=False, error=str(exc))
        launch['elapsed_seconds'] = time.monotonic() - start
        for name, content in [('stdout.log', stdout), ('stderr.log', stderr)]:
            (out / name).write_text(content.decode('utf-8', errors='replace') if isinstance(content, bytes) else content, encoding='utf-8')
        iteration.write(out / 'launch.json', launch)
    return launch

def main(argv=None):
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('mode', choices=['publish', 'reopen'])
    for key in ('iteration', 'case', 'output'):
        parser.add_argument('--' + key, required=True)
    parser.add_argument('--publish-report')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--timeout', type=int, default=1800)
    a = parser.parse_args(argv)
    try:
        result = dispatch(a.iteration, a.case, a.output, a.mode, a.publish_report, a.execute, a.timeout)
        print(json.dumps(result, ensure_ascii=False))
        return int(a.execute and not result['passed'])
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({'errors': [str(exc)]}, ensure_ascii=False))
        return 1

if __name__ == '__main__':
    raise SystemExit(main())
