"""Offline, pinned iteration review boards; never records visual approval."""
import argparse
import hashlib
import html
import json
import math
from pathlib import Path
import re
import struct
from urllib.parse import quote

ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def _load(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))

def _escape(value):
    return html.escape(str(value), quote=True)

def _regions(plan):
    regions = plan.get('review_regions', [])
    seen = set()
    for region in regions:
        key = region['id']
        if not re.fullmatch(r'[A-Za-z0-9_-]+', key) or key in seen:
            raise ValueError('invalid or repeated review region id')
        seen.add(key)
        for field in ('reference', 'cases'):
            rect = region[field]
            if not isinstance(rect, list) or len(rect) != 4 or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or not 0 <= v <= 1 for v in rect):
                raise ValueError('invalid normalized region')
            x,y,w,h = rect
            if w <= 0 or h <= 0 or x+w > 1 or y+h > 1:
                raise ValueError('normalized region outside frame')
    return regions

def dimensions(path):
    data = Path(path).read_bytes()
    if data[:8] == bytes.fromhex('89504e470d0a1a0a') and len(data) >= 24 and data[12:16] == b'IHDR':
        width,height = struct.unpack('>II',data[16:24])
    elif data[:2] == bytes.fromhex('ffd8'):
        offset=2
        while offset < len(data):
            if data[offset] != 255:
                raise ValueError('invalid JPEG marker')
            while offset < len(data) and data[offset] == 255:
                offset += 1
            if offset >= len(data):
                raise ValueError('truncated JPEG')
            marker=data[offset]; offset += 1
            if marker == 1 or 0xd0 <= marker <= 0xd8:
                continue
            if marker in (0xd9,0xda) or offset+2 > len(data):
                raise ValueError('JPEG dimensions unavailable')
            size=int.from_bytes(data[offset:offset+2],'big')
            if size < 2 or offset+size > len(data):
                raise ValueError('invalid JPEG segment')
            if marker in (0xc0,0xc1,0xc2,0xc3,0xc5,0xc6,0xc7,0xc9,0xca,0xcb,0xcd,0xce,0xcf):
                if size < 8:
                    raise ValueError('invalid JPEG SOF')
                height,width=struct.unpack('>HH',data[offset+3:offset+7])
                break
            offset += size
        else:
            raise ValueError('JPEG dimensions unavailable')
    else:
        raise ValueError('ROI requires PNG or JPEG dimensions')
    if width <= 0 or height <= 0:
        raise ValueError('invalid image dimensions')
    return width,height

def _case_records(report):
    return report['cases']

def build(directory, root=ROOT):
    from scripts import studio_iteration
    directory = Path(directory).resolve()
    result = studio_iteration.check(directory, root=root)
    if (isinstance(result, list) and result) or (isinstance(result, dict) and (result.get('passed') is False or result.get('ok') is False)):
        raise ValueError('iteration validation failed')
    names = ['manifest.json','inputs/study.json','inputs/plan.json','compiled-profile.json','run/report.json','run-link.json']
    docs = {name:_load(directory/name) for name in names}
    study,plan,report = (docs[n] for n in ('inputs/study.json','inputs/plan.json','run/report.json'))
    regions = _regions(plan)
    if report.get('passed') is not True or digest(directory/'run/report.json') != docs['run-link.json'].get('sha256'):
        raise ValueError('passing pinned run required')
    source = study['source']
    if study.get('kind', source.get('kind')) == 'video':
        raise ValueError('video requires an explicitly pre-extracted image artifact')
    reference = Path(source['path'])
    if not reference.is_absolute():
        reference = Path(root)/reference
    if digest(reference) != source['sha256']:
        raise ValueError('reference hash mismatch')
    ext = reference.suffix.lower()
    if ext not in ('.png','.jpg','.jpeg','.webp'):
        raise ValueError('unsupported reference image extension')
    run = (directory/'run').resolve()
    cases=[]
    for record in _case_records(report):
        key = record['id']
        if not re.fullmatch(r'[A-Za-z0-9_-]+', key):
            raise ValueError('unsafe case id')
        path = Path(record['path'])
        path = path if path.is_absolute() else run/path
        path = path.resolve()
        if path.parent != run or digest(path) != record['sha256']:
            raise ValueError('case image path or hash mismatch')
        cases.append(dict(id=key, image='../run/'+quote(path.name,safe=''), image_sha256=digest(path), metadata=record))
    if len({c['id'] for c in cases}) != len(cases):
        raise ValueError('duplicate case id')
    if regions:
        dimensions(reference)
        for case in cases:
            dimensions(run/Path(case['metadata']['path']).name)
    board=directory/'board'
    if board.exists():
        raise FileExistsError('board already exists')
    def panel(title,url,metadata,field,path):
        width,height = dimensions(path) if regions else (1,1)
        crops=''
        for region in regions:
            x,y,w,h=region[field]
            crops += '<p>'+_escape(region.get('label',region['id']))+' — independent semantic region; no pixel alignment</p><div class="crop" style="aspect-ratio:'+str(width*w/(height*h))+'"><img alt="region" src="'+url+'" style="width:'+str(100/w)+'%;height:'+str(100/h)+'%;left:'+str(-100*x/w)+'%;top:'+str(-100*y/h)+'%"></div>'
        return '<article><h2>'+_escape(title)+'</h2><img alt="'+_escape(title)+'" src="'+url+'">'+crops+'<details><summary>Image evidence and settings</summary><pre>'+_escape(json.dumps(metadata,ensure_ascii=False,indent=2))+'</pre></details></article>'
    body=panel('Reference','reference'+ext,source,'reference',reference)
    body+=''.join(panel(c['id'],c['image'],c['metadata'],'cases',run/Path(c['metadata']['path']).name) for c in cases)
    predictions='<ul>'+''.join('<li><strong>'+_escape(e['id'])+'</strong> vs '+_escape(e['compare_to'])+': '+_escape(e['prediction'])+'</li>' for e in plan.get('experiments',[]))+'</ul>'
    markup='<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width"><title>Iteration review</title><style>body{font:16px system-ui;background:#17191d;color:#eee;margin:24px}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}article{min-width:0;background:#24272d;padding:16px}img{width:100%;height:auto}pre{white-space:pre-wrap;overflow-wrap:anywhere}.crop{position:relative;overflow:hidden;aspect-ratio:1}.crop img{position:absolute;max-width:none}summary{cursor:pointer;padding:10px 0}</style><h1>Iteration review</h1><p>Status at board creation: AI review not reviewed; user approval pending. This tool does not visually inspect images. Reference does not establish physical author settings. Region crops are semantic comparisons only; proportions preserve source geometry.</p>'+predictions+'<div class="grid">'+body+'</div><details><summary>Frozen plan and controls</summary><pre>'+_escape(json.dumps(plan,ensure_ascii=False,indent=2))+'</pre></details>'
    pins={name:digest(directory/name) for name in names}
    board.mkdir()
    with (board/('reference'+ext)).open('xb') as stream:
        stream.write(reference.read_bytes())
    with (board/'index.html').open('x',encoding='utf-8') as stream:
        stream.write(markup)
    manifest=dict(schema_version=1,reference=dict(path='reference'+ext,sha256=digest(board/('reference'+ext))),cases=cases,input_pins=pins,html_sha256=digest(board/'index.html'),ai_review='not_reviewed',user_approval='pending')
    with (board/'manifest.json').open('x',encoding='utf-8') as stream:
        json.dump(manifest,stream,ensure_ascii=False,indent=2)
    return dict(board=str(board),manifest=str(board/'manifest.json'),manifest_sha256=digest(board/'manifest.json'))

def validate_board(directory):
    """Return errors for a board whose pinned content has changed."""
    directory=Path(directory).resolve()
    board=directory/'board'
    try:
        manifest=_load(board/'manifest.json')
        if digest(board/'index.html') != manifest['html_sha256']:
            raise ValueError('board HTML changed')
        reference=manifest['reference']
        path=(board/reference['path']).resolve()
        if path.parent != board or digest(path) != reference['sha256']:
            raise ValueError('board reference changed')
        for name,pin in manifest['input_pins'].items():
            path=(directory/name).resolve()
            if not path.is_relative_to(directory) or digest(path) != pin:
                raise ValueError('board input changed')
        for case in manifest['cases']:
            path=Path(case['metadata']['path']).resolve()
            if path.parent != (directory/'run').resolve() or digest(path) != case['image_sha256']:
                raise ValueError('board case image changed')
        return []
    except (ValueError,KeyError,TypeError,OSError) as error:
        return [str(error)]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--iteration',required=True)
    args=parser.parse_args()
    try:
        print(json.dumps(build(args.iteration),ensure_ascii=False))
    except (ValueError,KeyError,OSError,TypeError) as error:
        parser.exit(1,json.dumps({'error':str(error)},ensure_ascii=False)+'\n')

if __name__ == '__main__':
    main()



