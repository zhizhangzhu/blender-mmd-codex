import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import studio_lessons as lessons

class LessonTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(dir=os.environ.get('MMD_TEST_TEMP'))
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name); self.directory=self.root/'iteration'; self.directory.mkdir()
        self.registry=self.root/'studio.json'; self.registry.write_text(json.dumps({'capabilities':['untouched']}))
        lesson=dict(id='one',title='Title',scope=['still'],transfer_level='single_case',user_approval=False,findings=['observation'],hypothesis_outcomes=[],selection='baseline',limits=['single scene'],references=['study.json'])
        self.path=self.directory/'lesson.json'; self.path.write_text(json.dumps(lesson))
        (self.directory/'close-link.json').write_text(json.dumps({'path':str(self.path),'sha256':lessons.sha256(self.path)}))
    def register(self,**kwargs):
        return lessons.register(self.directory,self.registry,expected_registry_sha256=kwargs.get('expected',lessons.sha256(self.registry)),tags=kwargs.get('tags',['face']),route='lighting')
    @patch('scripts.studio_iteration.check',return_value=[])
    def test_register_retrieve(self,check):
        self.register(); registry=lessons.load(self.registry)
        self.assertEqual(registry['capabilities'],['untouched'])
        result=lessons.retrieve(registry,'face','lighting')
        self.assertEqual(len(result['lessons']),1); self.assertEqual(result['skipped'],[])
        self.assertIs(result['lessons'][0]['user_approval'],False)
        self.assertEqual(lessons.retrieve(registry,route='animation')['lessons'],[])
    @patch('scripts.studio_iteration.check',return_value=[])
    def test_chinese_natural_query_reuses_scoped_lesson(self,check):
        self.register(tags=['舞台','白衣'])
        for query in ('舞台灯光如何改善','缺词 白衣','舞台 白衣'):
            self.assertEqual(len(lessons.retrieve(self.registry,query,'lighting')['lessons']),1)
        self.assertEqual(lessons.retrieve(self.registry,'无关问题')['lessons'],[])
    @patch('scripts.studio_iteration.check',return_value=[])
    def test_nonboolean_closed_approval_rejected(self,check):
        doc=lessons.load(self.path);doc['user_approval']='approved';self.path.write_text(json.dumps(doc))
        (self.directory/'close-link.json').write_text(json.dumps({'path':str(self.path),'sha256':lessons.sha256(self.path)}))
        with self.assertRaises(ValueError):self.register()
    @patch('scripts.studio_iteration.check',return_value=[])
    def test_cas_duplicate(self,check):
        original=self.registry.read_bytes()
        with self.assertRaises(ValueError): self.register(expected='0'*64)
        self.assertEqual(self.registry.read_bytes(),original)
        self.register()
        with self.assertRaises(ValueError): self.register()
    @patch('scripts.studio_iteration.check',return_value=[])
    def test_tampering(self,check):
        self.register(); self.path.write_text('{}')
        result=lessons.retrieve(self.registry)
        self.assertEqual(result['lessons'],[]); self.assertEqual(len(result['skipped']),1)
        with self.assertRaises(ValueError): self.register()
    @patch('scripts.studio_iteration.check',return_value=['bad run'])
    def test_failed_iteration(self,check):
        with self.assertRaises(ValueError): self.register()
    def test_duplicate_registry(self):
        entry=dict(id='x',title='X',directory=str(self.directory),route='lighting',tags=[],lesson={'path':'x','sha256':'x'})
        with self.assertRaises(ValueError): lessons.retrieve({'lessons':[entry,entry]})

if __name__=='__main__': unittest.main()
