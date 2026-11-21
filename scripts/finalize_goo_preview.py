"""Record a successfully encoded preview, without decoding or inspecting the output video."""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
ROOT = Path('D:/codex/output/MMD-Goo-Wedding-v1')
info_path = ROOT / 'quick-5s-v1/preview-info.json'
info = json.loads(info_path.read_text(encoding='utf-8'))
assert info['user_requested_no_post_output_checks'] is True
assert info['output_frames'] == 150 and info['fps'] == 30
assert Path(info['video']).is_file()
state_path = REPO / 'catalog/current_state.json'
state = json.loads(state_path.read_text(encoding='utf-8'))
assert state['latest_quick_preview']['video'] == info['video']
state['active_iteration'].update(status='quick-preview-produced-post-output-qa-skipped-by-user',
                                 new_video_delivered=True, art_status='pending-user-review')
state['current_task'] = 'Goo迁移与插件/原生节点试验已完成，已实际输出一版1080p30五秒字幕原唱样片；未做输出后检查，美术待猪猪审看。'
state_path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
project_path = REPO / 'presets/projects/franken-duet-full-v1.json'
project = json.loads(project_path.read_text(encoding='utf-8-sig'))
project.setdefault('pre_goo_production', {k: project.get(k) for k in ('production_scene', 'integration_verification', 'render_output', 'status')})
project.update(production_scene=info['project'],
               integration_verification=str(ROOT / 'migration-preservation.json'),
               render_output=str(info_path.parent),
               status='Goo migrated working scene and one captioned five-second sample produced; post-output QA skipped; art pending; full song not delivered')
project_path.write_text(json.dumps(project, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
delivery = {'status': 'produced-post-output-checks-skipped', 'preview': info,
            'project': info['project'], 'launcher': str(ROOT / 'Start_Goo_Project.cmd'),
            'migration_report': str(ROOT / 'migration-preservation.json'),
            'plugin_report': str(ROOT / 'plugin-function-probe.json'),
            'user_art_approval': False, 'native_mme_runtime': False,
            'runtime_origin': 'Goo 5.2.1 unofficial NaMgAl-Studio community port',
            'limits': ['No post-output video decode or viewing at user request',
                       'Not every add-on feature tested; MMR registration only',
                       'Curvature Scene Rim remains disabled after unsuccessful primitive study',
                       'No new full-song physics or full-song render']}
(ROOT / 'delivery.json').write_text(json.dumps(delivery, ensure_ascii=False, indent=2), encoding='utf-8')
print('GOO_PREVIEW_DELIVERY_RECORDED', info['video'])
