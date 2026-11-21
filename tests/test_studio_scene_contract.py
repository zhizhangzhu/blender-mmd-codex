import copy
import unittest
from scripts import studio_scene_contract as c

class ContractTests(unittest.TestCase):
    def setUp(self):
        self.p={'schema_version':1,'id':'bench','source':{'path':'D:/source.blend','sha256':'a'*64},'runtime':'presets/runtime/goo-v1.json','scene':{'name':'Scene','camera':'Camera','expected_lens_mm':50,'registration':'none'},'actors':[{'id':'a','armature':'rigA','objects':['A'],'materials':{'skin':['shared']}},{'id':'b','armature':'rigB','objects':['B'],'materials':{'skin':['shared']}}],'switches':{'shade':{'kind':'node_input','material':'shared','node':'Shader','socket':'Strength','expected':1},'lamp':{'kind':'light_energy','object':'Lamp','expected':10}},'cases':[{'id':'base','frame':4290,'overrides':[{'switch':'shade','value':2}]}],'render':{'width':128,'height':128,'samples':1,'dof':'source','motion_blur':False},'limits':['bounded still']}
        self.i={'source':copy.deepcopy(self.p['source']),'runtime':{},'scene':{'name':'Scene','camera':'Camera','lens_mm':50},'objects':[{'name':'firstRig','type':'ARMATURE'},{'name':'rigA','type':'ARMATURE','bones':['same']},{'name':'rigB','type':'ARMATURE','bones':['same']},{'name':'A','type':'MESH','materials':['shared'],'armature_targets':['rigA']},{'name':'B','type':'MESH','materials':['shared'],'armature_targets':['rigB']},{'name':'Lamp','type':'LIGHT','energy':10}],'materials':[{'name':'shared','nodes':[{'name':'Shader','type':'VALUE','inputs':[{'name':'Strength','identifier':'Strength','value':1,'linked':False,'driven':False,'animated':False}]}]}],'compositor':[]}
    def test_two_rigs(self):
        self.assertTrue(c.bind(self.p,self.i)['passed'])
        self.i['objects'][4]['armature_targets']=['firstRig']
        self.assertFalse(c.bind(self.p,self.i)['passed'])
    def test_rna_float32_readback_keeps_meaningful_changes_detectable(self):
        self.assertTrue(c.equal(677.6, 677.5999755859375))
        self.assertFalse(c.equal(677.6, 677.61))
        self.assertFalse(c.equal(True, 1))
    def test_materials(self):
        p=copy.deepcopy(self.p);p['actors'][1]['materials']={'hair':['shared']};self.assertTrue(c.validate(p))
        p=copy.deepcopy(self.p);p['actors'][1]['materials']={'skin':['other']};self.assertFalse(c.bind(p,self.i)['passed'])
        self.i['objects'].append({'name':'stage','type':'MESH','materials':['shared']});r=c.bind(self.p,self.i);self.assertFalse(r['passed']);self.assertIn('stage',str(r['errors']))
    def test_node_rejections(self):
        for key,value in [('linked',True),('driven',True),('animated',True),('value',9)]:
            i=copy.deepcopy(self.i);i['materials'][0]['nodes'][0]['inputs'][0][key]=value
            self.assertFalse(c.bind(self.p,i)['passed'],key)
        for key in ('node','socket'):
            p=copy.deepcopy(self.p);p['switches']['shade'][key]='missing';self.assertFalse(c.bind(p,self.i)['passed'])
    def test_explicit_identifier_selects_among_repeated_display_names(self):
        i=copy.deepcopy(self.i)
        i['materials'][0]['nodes'][0]['inputs'].append(dict(i['materials'][0]['nodes'][0]['inputs'][0],identifier='OtherIdentifier'))
        self.assertFalse(c.bind(self.p,i)['passed'])
        p=copy.deepcopy(self.p);p['switches']['shade']['socket_match']='identifier'
        self.assertTrue(c.bind(p,i)['passed'])
        p['switches']['shade']['socket_match']='first'
        self.assertTrue(c.validate(p))
    def test_source_and_expected(self):
        self.i['source']['sha256']='b'*64;self.assertFalse(c.bind(self.p,self.i)['passed'])
        self.i['source']=copy.deepcopy(self.p['source']);self.i['objects'][-1]['energy']=11;self.assertFalse(c.bind(self.p,self.i)['passed'])
    def test_invalid_values(self):
        for value in (float('nan'),float('inf'),True,-1):
            p=copy.deepcopy(self.p);p['switches']['lamp']['expected']=value;self.assertTrue(c.validate(p))
            p=copy.deepcopy(self.p);p['cases'][0]['overrides']=[{'switch':'lamp','value':value}];self.assertTrue(c.validate(p))
        for value in (float('nan'),float('inf'),True):
            p=copy.deepcopy(self.p);p['render']['samples']=value;self.assertTrue(c.validate(p))
    def test_case_guards(self):
        for key,value in [('id','../escape'),('frame',True),('overrides',[{'switch':'unknown','value':1}]),('overrides',[{'switch':'shade','value':1}]*2)]:
            p=copy.deepcopy(self.p);p['cases'][0][key]=value;self.assertTrue(c.validate(p))
        p=copy.deepcopy(self.p);p['id']='../escape';self.assertTrue(c.validate(p))
        p=copy.deepcopy(self.p);p['switches']['../escape']=p['switches'].pop('shade');self.assertTrue(c.validate(p))
        p=copy.deepcopy(self.p);p['render']['motion_blur']=True;self.assertTrue(c.validate(p))
    def test_no_mutations(self):
        before=copy.deepcopy(self.p);c.validate(self.p);c.bind(self.p,self.i);plan=c.plan(self.p);plan['source']['path']='changed';self.assertEqual(before,self.p)
    def test_malformed(self):
        for value in (None, [], {}, {'schema_version':1}):
            self.assertTrue(c.validate(value));self.assertFalse(c.bind(value,{})['passed'])
        for value in (None, [], {}):self.assertFalse(c.bind(self.p,value)['passed'])

    def test_review_guards(self):
        p=copy.deepcopy(self.p);p['switches']['shade']['expected']=True;p['cases'][0]['overrides'][0]['value']=False
        self.assertFalse(c.validate(p))
        for value in (float('nan'),float('inf'),[True]):
            p=copy.deepcopy(self.p);p['switches']['shade']['expected']=value;p['cases'][0]['overrides']=[];self.assertTrue(c.validate(p))
        i=copy.deepcopy(self.i);i['materials'][0]['nodes'][0]['inputs']*=2;self.assertFalse(c.bind(self.p,i)['passed'])
        i=copy.deepcopy(self.i);i['objects'][3]['scene_local']=False;self.assertFalse(c.bind(self.p,i)['passed'])
        for flag in ('driven','animated'):
            i=copy.deepcopy(self.i);i['objects'][-1]['control_protection']={'energy':{flag:True}};self.assertFalse(c.bind(self.p,i)['passed'])
        p=copy.deepcopy(self.p);p['cases'].append(dict(p['cases'][0],id='BASE'));self.assertTrue(c.validate(p))
    def test_glow_shared_and_false(self):
        p=copy.deepcopy(self.p);p['switches']['glow']={'kind':'glow_bypass','nodes':[{'tree':'compositor','scene':'Scene','node':'Glow','image_output':'Image','glare_output':'Glare'}]};p['cases'][0]['overrides']=[{'switch':'glow','value':False}];self.assertTrue(c.validate(p))
        p['cases'][0]['overrides'][0]['value']=True
        i=copy.deepcopy(self.i);i['compositor']=[{'scene':'Scene','tree_users':['Scene','Other'],'nodes':[{'name':'Glow','type':'GLARE','outputs':['Image','Glare']}]}];self.assertFalse(c.bind(p,i)['passed'])
        i['compositor'][0]['tree_users']=['Scene'];self.assertTrue(c.bind(p,i)['passed'])
    def test_optimized_validation(self):
        import subprocess
        import sys
        result=subprocess.run([sys.executable,'-O','-c',"from scripts.studio_scene_contract import validate; raise SystemExit(0 if validate({'schema_version':1}) else 1)"],cwd=c.ROOT,capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)

if __name__=='__main__': unittest.main()
