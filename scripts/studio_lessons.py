"""Explicit registration and integrity-checked retrieval of single-case lessons."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import tempfile

ROOT=Path(__file__).resolve().parents[1]

def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))

def _entries(registry):
    entries=registry.get('lessons',[])
    if not isinstance(entries,list):
        raise ValueError('lessons must be a list')
    ids=set(); directories=set()
    for entry in entries:
        if not isinstance(entry,dict) or not all(isinstance(entry.get(key),str) and entry[key] for key in ('id','title','directory','route')):
            raise ValueError('invalid lesson registry entry')
        if entry['id'] in ids or str(Path(entry['directory']).resolve()) in directories:
            raise ValueError('duplicate registered lesson')
        ids.add(entry['id']); directories.add(str(Path(entry['directory']).resolve()))
        if not isinstance(entry.get('tags'),list) or any(not isinstance(tag,str) for tag in entry['tags']):
            raise ValueError('invalid lesson tags')
        pin=entry.get('lesson')
        if not isinstance(pin,dict) or not isinstance(pin.get('path'),str) or not isinstance(pin.get('sha256'),str):
            raise ValueError('invalid lesson pin')
        if type(entry.get('user_approval')) is not bool or entry.get('transfer_level') != 'single_case' or not isinstance(entry.get('scope'),list):
            raise ValueError('invalid lesson scope/approval')
    return entries

def _verified(directory):
    from scripts import studio_iteration
    directory=Path(directory).resolve()
    errors=studio_iteration.check(directory)
    if errors:
        raise ValueError('iteration check failed: '+str(errors))
    link=load(directory/'close-link.json')
    lesson_path=directory/'lesson.json'
    if Path(link['path']).resolve()!=lesson_path or sha256(lesson_path)!=link['sha256']:
        raise ValueError('closed lesson pin mismatch')
    lesson=load(lesson_path)
    if lesson.get('transfer_level')!='single_case':
        raise ValueError('only single_case lessons may be registered')
    if type(lesson.get('user_approval')) is not bool or not isinstance(lesson.get('scope'),list):
        raise ValueError('lesson requires explicit boolean approval and scope')
    return lesson,dict(path=str(lesson_path),sha256=link['sha256'])

def register(directory, registry_path=ROOT/'catalog/studio.json', *, expected_registry_sha256, tags, route):
    directory=Path(directory).resolve(); registry_path=Path(registry_path)
    if not isinstance(tags,list) or any(not isinstance(tag,str) or not tag.strip() for tag in tags) or not isinstance(route,str) or not route.strip():
        raise ValueError('nonempty route and string tags required')
    if sha256(registry_path)!=expected_registry_sha256:
        raise ValueError('registry CAS mismatch')
    registry=load(registry_path); entries=_entries(registry)
    lesson,pin=_verified(directory)
    if any(entry['id']==lesson['id'] or Path(entry['directory']).resolve()==directory for entry in entries):
        raise ValueError('lesson already registered')
    entry=dict(id=lesson['id'],title=lesson['title'],directory=str(directory),lesson=pin,route=route,tags=tags,scope=lesson['scope'],transfer_level='single_case',user_approval=lesson['user_approval'])
    registry['lessons']=entries+[entry]
    _entries(registry)
    temporary=None
    try:
        with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',dir=registry_path.parent,prefix='.studio-lessons-',suffix='.tmp',delete=False) as stream:
            temporary=Path(stream.name)
            json.dump(registry,stream,ensure_ascii=False,indent=2)
            stream.write('\n'); stream.flush(); os.fsync(stream.fileno())
        if sha256(registry_path)!=expected_registry_sha256:
            raise ValueError('registry CAS mismatch before replacement')
        os.replace(temporary,registry_path)
    finally:
        if temporary is not None and temporary.exists(): temporary.unlink()
    return entry

def retrieve(registry, query='', route=None, root=ROOT):
    if not isinstance(registry,dict): registry=load(registry)
    entries=_entries(registry); matches=[]; skipped=[]
    for entry in entries:
        if route is not None and entry['route']!=route: continue
        if query:
            folded=query.casefold()
            haystack=json.dumps(entry,ensure_ascii=False).casefold()
            if not (any(token in haystack for token in folded.split()) or
                    any(len(tag.strip()) >= 2 and tag.casefold() in folded for tag in entry['tags'])):
                continue
        try:
            directory=Path(entry['directory'])
            if not directory.is_absolute(): directory=Path(root)/directory
            lesson,pin=_verified(directory)
            if pin!=entry['lesson'] or lesson['id']!=entry['id'] or lesson['user_approval']!=entry['user_approval'] or lesson['scope']!=entry['scope']:
                raise ValueError('registry differs from closed lesson')
            fields=('id','title','findings','hypothesis_outcomes','selection','scope','limits','references','user_approval','transfer_level')
            matches.append({**{key:lesson[key] for key in fields},'lesson':pin,'route':entry['route'],'tags':entry['tags']})
        except (ValueError,KeyError,TypeError,OSError) as error:
            skipped.append({'id':entry['id'],'error':str(error)})
    return {'lessons':matches,'skipped':skipped}

def main(argv=None):
    parser=argparse.ArgumentParser(__doc__)
    sub=parser.add_subparsers(dest='command',required=True)
    reg=sub.add_parser('register'); reg.add_argument('--iteration',required=True); reg.add_argument('--expected-sha256',required=True); reg.add_argument('--tags',nargs='*',default=[]); reg.add_argument('--route',required=True)
    query=sub.add_parser('query'); query.add_argument('--query',default=''); query.add_argument('--route')
    for child in (reg,query): child.add_argument('--registry',default=str(ROOT/'catalog/studio.json'))
    args=parser.parse_args(argv)
    try:
        result=register(args.iteration,args.registry,expected_registry_sha256=args.expected_sha256,tags=args.tags,route=args.route) if args.command=='register' else retrieve(args.registry,args.query,args.route)
        print(json.dumps(result,ensure_ascii=False)); return 0
    except (ValueError,KeyError,TypeError,OSError) as error:
        print(json.dumps({'errors':[str(error)]},ensure_ascii=False)); return 1

if __name__=='__main__': raise SystemExit(main())
