import json
import os
import struct
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import studio_review_board as board

class BoardTests(unittest.TestCase):
    def fixture(self, root):
        (root/'inputs').mkdir(); (root/'run').mkdir()
        ref=root/'ref.png'; ref.write_bytes(bytes.fromhex('89504e470d0a1a0a')+struct.pack('>I',13)+b'IHDR'+struct.pack('>II',160,90))
        image=root/'run'/'base.png'; image.write_bytes(ref.read_bytes())
        docs={'manifest.json':{},'compiled-profile.json':{},'run-link.json':{},'inputs/study.json':{'source':{'path':str(ref),'sha256':board.digest(ref)}},'inputs/plan.json':{'goal':'<script>alert(1)</script>'},'run/report.json':{'passed':True,'cases':[{'id':'baseline','path':str(image),'sha256':board.digest(image)}]}}
        for name,data in docs.items(): (root/name).write_text(json.dumps(data),encoding='utf-8')
        (root/'run-link.json').write_text(json.dumps({'sha256':board.digest(root/'run/report.json')}))
        return ref,image
    @patch('scripts.studio_iteration.check',return_value=[])
    def test_safe_board(self, check):
        with tempfile.TemporaryDirectory(dir=os.environ.get('MMD_TEST_TEMP')) as directory:
            root=Path(directory); self.fixture(root)
            board.build(root)
            text=(root/'board/index.html').read_text(encoding='utf-8')
            self.assertNotIn('<script>',text); self.assertIn('&lt;script&gt;',text)
            self.assertIn('not reviewed',text); self.assertIn('pending',text)
            self.assertLess(text.index('class="grid"'), text.index('Frozen plan and controls'))
            with self.assertRaises(FileExistsError): board.build(root)
    @patch('scripts.studio_iteration.check',return_value=[])
    def test_built_board_detects_changed_evidence(self, check):
        with tempfile.TemporaryDirectory(dir=os.environ.get('MMD_TEST_TEMP')) as directory:
            root=Path(directory); self.fixture(root); board.build(root)
            self.assertEqual([],board.validate_board(root))
            for name in ('board/index.html','board/reference.png','run/base.png','compiled-profile.json'):
                path=root/name; original=path.read_bytes()
                path.write_bytes(b'changed evidence')
                self.assertTrue(board.validate_board(root),name)
                path.write_bytes(original)
            self.assertEqual([],board.validate_board(root))
    @patch('scripts.studio_iteration.check',return_value=[])
    def test_tampering(self, check):
        for target in (0,1):
            with tempfile.TemporaryDirectory(dir=os.environ.get('MMD_TEST_TEMP')) as directory:
                root=Path(directory); files=self.fixture(root); files[target].write_bytes(b'changed')
                with self.assertRaises(ValueError): board.build(root)
                self.assertFalse((root/'board').exists())
    @patch('scripts.studio_iteration.check',return_value=[])
    def test_video_and_external_path(self, check):
        for video in (True,False):
            with tempfile.TemporaryDirectory(dir=os.environ.get('MMD_TEST_TEMP')) as directory:
                root=Path(directory); ref,image=self.fixture(root)
                if video:
                    path=root/'inputs/study.json'; doc=json.loads(path.read_text()); doc['kind']='video'
                else:
                    path=root/'run/report.json'; doc=json.loads(path.read_text()); doc['cases'][0].update(path=str(ref),sha256=board.digest(ref))
                path.write_text(json.dumps(doc))
                (root/'run-link.json').write_text(json.dumps({'sha256':board.digest(root/'run/report.json')}))
                with self.assertRaises(ValueError): board.build(root)
                self.assertFalse((root/'board').exists())

    @patch('scripts.studio_iteration.check',return_value=[])
    def test_crop_geometry(self, check):
        with tempfile.TemporaryDirectory(dir=os.environ.get('MMD_TEST_TEMP')) as directory:
            root=Path(directory); ref,image=self.fixture(root)
            self.assertEqual(board.dimensions(ref),(160,90))
            plan={'review_regions':[{'id':'face','reference':[0,0,.5,.5],'cases':[0,0,.5,.5]}]}
            (root/'inputs/plan.json').write_text(json.dumps(plan))
            board.build(root)
            self.assertIn('aspect-ratio:1.7777777777777777',(root/'board/index.html').read_text())
            bad=root/'bad.png'; bad.write_bytes(b'bad')
            with self.assertRaises(ValueError): board.dimensions(bad)

    def test_regions(self):
        for regions in ([{'id':'x','reference':[0,0,2,1],'cases':[0,0,1,1]}], [{'id':'x','reference':[0,0,1,1],'cases':[0,0,1,1]}]*2):
            with self.assertRaises(ValueError): board._regions({'review_regions':regions})

if __name__=='__main__': unittest.main()
