"""Pure-Python checks for worker guards; real Blender cases are separate evidence."""

import importlib.util
import os
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS
import unittest
from unittest.mock import patch


class WorkerGuardTests(unittest.TestCase):
    def setUp(self):
        self.bpy = ModuleType("bpy")
        self.bpy.data = NS(objects=[], scenes=[])
        path = Path(__file__).resolve().parents[1] / "scripts/studio_scene_worker.py"
        spec = importlib.util.spec_from_file_location("isolated_studio_worker", path)
        self.worker = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, {"bpy": self.bpy}):
            spec.loader.exec_module(self.worker)

    def test_viewport_only_simulation_is_also_refused(self):
        mod = NS(name="Cloth", type="CLOTH", show_render=False, show_viewport=True)
        self.bpy.data.objects = [NS(name="actor", modifiers=[mod])]
        self.assertTrue(self.worker.simulation_hazards())
        mod.show_viewport = False
        self.assertEqual([], self.worker.simulation_hazards())
        mod.show_render = True
        self.assertTrue(self.worker.simulation_hazards())

    def test_nested_geometry_simulation_is_detected(self):
        inner = NS(nodes=[NS(type="SIMULATION_OUTPUT", bl_idname="GeometryNodeSimulationOutput")], as_pointer=lambda: 2, name="inner")
        outer = NS(nodes=[NS(type="GROUP", bl_idname="GeometryNodeGroup", node_tree=inner)], as_pointer=lambda: 1)
        mod = NS(name="GN", type="NODES", show_render=True, show_viewport=True, node_group=outer)
        self.bpy.data.objects = [NS(name="actor", modifiers=[mod])]
        self.assertTrue(any("geometry simulation" in e for e in self.worker.simulation_hazards()))

    def test_disabled_but_animated_simulation_is_refused_before_sampling(self):
        mod = NS(name="Cloth", type="CLOTH", show_render=False, show_viewport=False)
        self.bpy.data.objects = [NS(name="actor", modifiers=[mod],
            animation_data=NS(action=object(), nla_tracks=[], drivers=[]))]
        self.assertTrue(any("animated simulation" in e for e in self.worker.simulation_hazards()))

    def test_recursive_file_outputs_are_muted_without_touching_image_outputs(self):
        node = NS(type="OUTPUT_FILE", name="inherited", mute=False)
        inner = NS(nodes=[node], as_pointer=lambda: 2, name="inner")
        outer = NS(nodes=[NS(type="GROUP", node_tree=inner)], as_pointer=lambda: 1)
        scene = NS(name="scene", compositing_node_group=outer, render=NS(use_sequencer=True))
        self.bpy.data.scenes = [scene]
        records = self.worker.silence_outputs()
        self.assertTrue(node.mute)
        self.assertFalse(scene.render.use_sequencer)
        self.assertEqual("inner", records[0]["tree"])

    def test_ambiguous_socket_is_rejected(self):
        node = NS(inputs=[NS(name="Value", identifier="Value"), NS(name="Value", identifier="Value_001")])
        with self.assertRaises(ValueError):
            self.worker.find_socket(node, "Value")
        self.assertEqual("Value_001", self.worker.find_socket(node, "Value_001").identifier)
        self.assertEqual("Value", self.worker.find_socket(node, "Value", identifier_only=True).identifier)

    def test_verify_cannot_pass_without_a_baseline(self):
        with self.assertRaises(ValueError):
            self.worker.verification_baseline({"id": "fixture"})

    def test_goo_descriptive_version_uses_exact_machine_tuple(self):
        self.bpy.app = NS(version=(5, 2, 1), build_hash=b"fixed-build")
        self.bpy.types = NS(ShaderNodeShaderInfo=object())
        self.bpy.context = NS(preferences=NS(filepaths=NS(use_scripts_auto_execute=True)))
        runtime = dict(version="5.2.1 LTS community Goo port", version_tuple=[5, 2, 1],
                       build_hash="fixed-build", user_config=str(Path.cwd()),
                       user_scripts=str(Path.cwd()), required_node_types=["ShaderNodeShaderInfo"])
        with patch.dict(os.environ, BLENDER_USER_CONFIG=str(Path.cwd()), BLENDER_USER_SCRIPTS=str(Path.cwd())):
            self.worker.prepare_runtime(runtime, "none")
            self.assertFalse(self.bpy.context.preferences.filepaths.use_scripts_auto_execute)
            for field, value in [("version_tuple", [5, 3, 0]), ("build_hash", "other"),
                                 ("required_node_types", ["MissingGooNode"])]:
                with self.subTest(field=field), self.assertRaises(ValueError):
                    self.worker.prepare_runtime(dict(runtime, **{field: value}), "none")


if __name__ == "__main__":
    unittest.main()
