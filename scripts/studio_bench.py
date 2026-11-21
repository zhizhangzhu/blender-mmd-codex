"""Opt-in, bounded Blender scene benchmark launcher (stdlib only)."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / 'scripts' / 'studio_scene_worker.py'
MODES = ('inspect', 'render', 'verify')


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def command(runtime, mode, profile, output, worker=None):
    if mode not in MODES:
        raise ValueError('unsupported mode')
    args = [str(runtime['executable']), '--background', '--factory-startup',
            '--disable-autoexec', '--python-exit-code', '1', '--python',
            str(Path(worker or WORKER).resolve()), '--', '--mode', mode,
            '--profile', str(Path(profile).resolve()), '--output', str(Path(output).resolve())]
    env = os.environ.copy()
    env.update(BLENDER_USER_CONFIG=str(runtime['user_config']),
               BLENDER_USER_SCRIPTS=str(runtime['user_scripts']))
    return args, env


def dispatch(runtime, mode, profile_path, source, output, execute=False, timeout=600):
    if isinstance(timeout, bool) or not isinstance(timeout, (int, float)) or not math.isfinite(timeout) or not 1 <= timeout <= 3600:
        raise ValueError('timeout must be finite and between 1 and 3600 seconds')
    profile_path, source, output = map(lambda p: Path(p).resolve(), (profile_path, source, output))
    if output == source or source.is_relative_to(output):
        raise ValueError('output must not contain or equal the source')
    for key in ('executable', 'user_config', 'user_scripts', 'version', 'build_hash'):
        if not isinstance(runtime.get(key), str) or not runtime[key]:
            raise ValueError('invalid runtime field: ' + key)
    args, env = command(runtime, mode, profile_path, output)
    before = sha256(source)
    report = dict(command=args, runtime=runtime, mode=mode, source=str(source),
                  profile=str(profile_path), profile_sha256=sha256(profile_path),
                  source_sha256_before=before, execution='not_dispatched', passed=False,
                  environment={k: env[k] for k in ('BLENDER_USER_CONFIG', 'BLENDER_USER_SCRIPTS')})
    if not execute:
        return report
    for key in ('executable', 'user_config', 'user_scripts'):
        path = Path(runtime[key])
        if not path.is_absolute() or not (path.is_file() if key == 'executable' else path.is_dir()):
            raise ValueError('runtime path missing or invalid: ' + key)
    report['worker_sha256'] = sha256(WORKER)
    runtime_path = json.loads(profile_path.read_text(encoding='utf-8-sig')).get('runtime')
    report['runtime_sha256'] = sha256(ROOT / runtime_path) if runtime_path else None
    if output.exists():
        raise ValueError('execution requires a new output directory')
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    report.update(execution='dispatched', returncode=None, timeout=False,
                  worker_report=str(output / 'report.json'))
    stdout = stderr = ''
    try:
        result = subprocess.run(args, env=env, shell=False, capture_output=True,
                                text=True, encoding='utf-8', errors='replace', timeout=timeout)
        stdout, stderr = result.stdout, result.stderr
        report['returncode'] = result.returncode
        worker_report = json.loads((output / 'report.json').read_text(encoding='utf-8'))
        report['passed'] = result.returncode == 0 and worker_report.get('passed') is True
    except subprocess.TimeoutExpired as exc:
        report.update(timeout=True, error='process timeout')
        stdout, stderr = exc.stdout or '', exc.stderr or ''
    except Exception as exc:
        report['error'] = str(exc)
    finally:
        report['elapsed_seconds'] = time.monotonic() - start
        try:
            report['source_sha256_after'] = sha256(source)
        except OSError as exc:
            report['source_sha256_after'] = None
            report['error'] = str(exc)
        try:
            report['profile_sha256_after'] = sha256(profile_path)
        except OSError:
            report['profile_sha256_after'] = None
        if report['profile_sha256_after'] != report['profile_sha256']:
            report.update(passed=False, error='profile changed during execution')
        if report['source_sha256_after'] != before:
            report.update(passed=False, error='source changed during execution')
        for name, content in (('stdout.log', stdout), ('stderr.log', stderr)):
            (output / name).write_text(content.decode('utf-8', errors='replace') if isinstance(content, bytes) else content, encoding='utf-8')
        (output / 'launch.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=('plan',) + MODES)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--output')
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--timeout', type=float, default=600)
    args = parser.parse_args(argv)
    try:
        from scripts import studio_scene_contract as contract
        profile = contract.load(args.profile)
        errors = contract.validate(profile, root=ROOT, check_source=True)
        if errors:
            raise ValueError(str(errors))
        runtime_path = Path(profile['runtime'])
        if not runtime_path.is_absolute():
            runtime_path = ROOT / runtime_path
        runtime = json.loads(runtime_path.read_text(encoding='utf-8-sig'))
        if args.mode != 'plan' and not args.output:
            raise ValueError('--output is required')
        report = dispatch(runtime, 'inspect' if args.mode == 'plan' else args.mode,
                          args.profile, profile['source']['path'],
                          args.output or ROOT / 'planned-output',
                          execute=args.execute and args.mode != 'plan', timeout=args.timeout)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0 if report['execution'] == 'not_dispatched' or report['passed'] else 1
    except Exception as exc:
        print(json.dumps({'passed': False, 'error': str(exc)}, ensure_ascii=False))
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

