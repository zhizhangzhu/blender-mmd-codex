"""Write local user launchers and migration facts; never claim video completion before encoding."""
import json
import shutil
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path('D:/codex/output/MMD-Goo-Wedding-v1')
RUNTIME = Path('D:/codex/workspace/goo-engine/5.2.1-community')
config = json.loads((REPO / 'presets/runtime/goo-v1.json').read_text(encoding='utf-8'))
prep = json.loads((ROOT / 'production-v1/preparation.json').read_text(encoding='utf-8'))

shutil.copyfile(REPO / 'scripts/goo_runtime.py', ROOT / 'Goo_Startup.py')
shutil.copyfile(REPO / 'docs/GOO_ENGINE_MIGRATION.md', ROOT / 'Goo_Migration_Notes.md')
shutil.copyfile(REPO / 'docs/CREDITS_AKSINIYA_IKHOR.md', ROOT / 'Original_Character_Stage_Credits.md')
(ROOT / 'runtime.json').write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding='utf-8')
gui = '\r\n'.join([
    '@echo off',
    f'set "BLENDER_USER_CONFIG={RUNTIME / "portable/config"}"',
    f'set "BLENDER_USER_SCRIPTS={RUNTIME / "portable/scripts"}"',
    f'start "" "{config["executable"]}" --disable-autoexec --python "%~dp0Goo_Startup.py" "%~dp0production-v1\\Franken_Duet_Goo_Wedding.blend"',
    ''
])
(ROOT / 'Start_Goo_Project.cmd').write_text(gui, encoding='ascii')
render = '\r\n'.join([
    '@echo off',
    'set "PYTHONIOENCODING=utf-8"',
    f'cd /d "{REPO}"',
    '"C:\\Users\\Administrator\\AppData\\Local\\Programs\\Python\\Python39\\python.exe" scripts\\run_goo_wedding_preview.py',
    'pause', ''
])
(ROOT / 'Render_5s_Subtitled.cmd').write_text(render, encoding='ascii')
(ROOT / 'README.txt').write_text(
    '猪猪，这里是新的 Goo 工作工程。\n'
    '双击 Start_Goo_Project.cmd：以独立 Goo 5.2.1 社区版打开工程并注册插件。\n'
    '不建议直接双击 blend，以免 Windows 使用原 Blender 打开 Goo 专属节点。\n'
    'production-v1/complete-4290.png 是已实际生成的迁移同帧测试图。\n'
    '五秒字幕视频完成后位于 quick-5s-v1；是否完成以其中 preview-info.json 为准。\n'
    'Render_5s_Subtitled.cmd 是固定一次性渲染入口，已有输出会拒绝覆盖。\n'
    '运行时来自 NaMgAl-Studio 的 Goo 5.2.1 非官方移植版，不是 DillonGoo 原版二进制。\n'
    '插件测试和仍未验证的功能见 plugin-function-probe.json 与 Goo_Migration_Notes.md。\n', encoding='utf-8')

state_path = REPO / 'catalog/current_state.json'
state = json.loads(state_path.read_text(encoding='utf-8-sig'))
if state.get('active_iteration', {}).get('id') != 'goo-wedding-v1':
    state.setdefault('iteration_history', []).append(state.get('active_iteration', {}))
    state['active_iteration'] = {
        'id': 'goo-wedding-v1', 'status': 'rendering-quick-preview', 'user_authorized': True,
        'project': prep['project'], 'project_sha256': prep['project_sha256'],
        'guide': 'docs/GOO_ENGINE_MIGRATION.md', 'new_video_delivered': False,
        'scope': 'Goo migration and one 1080p30 five-second subtitled sample with original vocal audio',
        'post_output_checks': 'skipped at user request', 'art_status': 'pending-user-review'}
state['production_runtime'] = config
if not (ROOT / 'quick-5s-v1/preview-info.json').is_file():
    state['current_task'] = '已完成Goo工程迁移、独立重开与插件/原生节点试验，正在实际渲染一版1080p30五秒字幕原唱样片；编码完成前不称视频交付。'
state['latest_still'] = {
    'entry_id': 'goo-wedding-v1', 'project': prep['project'], 'project_sha256': prep['project_sha256'],
    'image': str(ROOT / 'production-v1/complete-4290.png'),
    'scope': {'frame': 4290, 'resolution': [1920, 1080], 'samples': 24, 'dof': True, 'motion_blur': False},
    'technical_status': 'actual Goo render and independent migration preservation checks complete',
    'art_status': 'pending-user-review', 'user_art_approval': False,
    'runtime': config['executable'], 'preparation': str(ROOT / 'production-v1/preparation.json')}
state['preset_reuse_policy']['goo_runtime_added'] = 'presets/runtime/goo-v1.json'
state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print('GOO_WORKING_PROJECT_PACKAGED', ROOT)
