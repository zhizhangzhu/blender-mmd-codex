"""Restore a blue/cyan procedural daytime World in the pinned duet copy.

Explicit opt-in API: apply(scene, settings=None), set_enabled(scene, bool),
remove(scene). The existing World is copied; its original datablock is never
edited. No stage/material/object, actor, camera, lamp, compositor, preference,
image or file is written. The caller owns rendering and any probe rebake.

Clean v2 already has the procedural sky from hesperides_reference_rebuild.py;
the night art pass changed its color ramp and Background strength. This module
reuses that exact Noise -> smooth horizon cloud mask -> ramp -> Background
structure. It restores bright blue/cyan and broader soft clouds without a new
HDRI, download, sky mesh, generated image, star shader or full scene builder.

The two existing spatial-light-mote meshes are independent of the sky. They
remain unchanged and are reported for the caller's separate stage decision.
Existing EEVEE probe caches are not invalidated or rebaked here; changing a
World does not certify that cached indirect lighting matches the new sky.
"""

import copy
import hashlib
import json
import math
from pathlib import Path

import bpy

PREFIX = "Portrait daylight | "
STATE = "portrait_day_sky_state"
SOURCE_SHA256 = "0ec95ee7162512ffc405a2a7337b355caf62cd993b3d8302886ee59e1561d9d4"
EXPECTED_WORLD = "Reference | cyan sky environment"
MOTES = (
    "Reference | spatial light motes",
    "Reference | spatial light motes.001",
)
DEFAULT_SETTINGS = {
    "id": "portrait-day-sky-v1",
    "enabled": True,
    "verify_source_hash": True,
    "world_strength": 0.95,
    # Linear RGB. Base recovers the blue of the local Ray-reference study;
    # clouds add soft pale cyan rather than a uniformly white window.
    "sky_blue": [0.005, 0.20, 0.52, 1.0],
    "sky_cloud": [0.18, 0.64, 0.86, 1.0],
    "noise_scale": 9.0,
    "noise_detail": 2.4,
    "noise_roughness": 0.62,
    "noise_distortion": 0.0,
    "cloud_density_range": [0.40, 0.64],
    "cloud_height_range": [0.015, 0.48],
}


def _number(value, label, low=0.0, high=1.0):
    value = float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError("Invalid daylight sky " + label)
    return value


def _settings(overrides):
    settings = copy.deepcopy(DEFAULT_SETTINGS)
    for key, value in (overrides or {}).items():
        if key not in settings:
            raise ValueError("Unknown daylight sky setting: " + key)
        settings[key] = copy.deepcopy(value)
    if not isinstance(settings["enabled"], bool):
        raise TypeError("Daylight sky enabled must be boolean")
    _number(settings["world_strength"], "World strength", 0, 4)
    for key in ("sky_blue", "sky_cloud"):
        color = settings[key]
        if len(color) != 4 or color[3] != 1:
            raise ValueError("Daylight sky colors require RGBA with alpha one")
        for component in color[:3]:
            _number(component, key + " linear RGB", 0, 2)
    for key in ("cloud_density_range", "cloud_height_range"):
        lo, hi = settings[key]
        _number(lo, key, -1 if key == "cloud_height_range" else 0, 1)
        _number(hi, key, -1 if key == "cloud_height_range" else 0, 1)
        if not lo < hi:
            raise ValueError("Expected increasing daylight sky range: " + key)
    _number(settings["noise_scale"], "noise scale", 0.01, 100)
    _number(settings["noise_detail"], "noise detail", 0, 15)
    _number(settings["noise_roughness"], "noise roughness")
    _number(settings["noise_distortion"], "noise distortion", 0, 10)
    return settings


def _single_source(socket):
    if len(socket.links) != 1:
        raise ValueError("Daylight sky expects one audited input link")
    return socket.links[0].from_node


def _contract(world):
    """Resolve the existing source graph by types and links, not localized names."""
    if not world or not world.use_nodes or not world.node_tree:
        raise ValueError("Missing existing node-based sky World")
    tree = world.node_tree
    outputs = [n for n in tree.nodes if n.type == "OUTPUT_WORLD" and n.is_active_output]
    if len(outputs) != 1 or outputs[0].inputs["Volume"].is_linked:
        raise ValueError("Daylight sky requires the existing volume-free World")
    background = _single_source(outputs[0].inputs["Surface"])
    if background.type != "BACKGROUND":
        raise ValueError("Unexpected original World Surface")
    ramp = _single_source(background.inputs["Color"])
    if ramp.type != "VALTORGB" or len(ramp.color_ramp.elements) != 2:
        raise ValueError("Expected original two-color sky ramp")
    clouds = _single_source(ramp.inputs[0])
    if clouds.type != "MATH" or clouds.operation != "MULTIPLY":
        raise ValueError("Expected original noise-times-horizon cloud mask")
    ranges = [_single_source(clouds.inputs[i]) for i in (0, 1)]
    if any(n.type != "MAP_RANGE" for n in ranges):
        raise ValueError("Expected original density and horizon ranges")
    density = next(
        (n for n in ranges if _single_source(n.inputs["Value"]).type == "TEX_NOISE"),
        None,
    )
    horizon = next(
        (n for n in ranges if _single_source(n.inputs["Value"]).type == "SEPXYZ"), None
    )
    if density is None or horizon is None or density == horizon:
        raise ValueError("Cannot identify original cloud density/horizon controls")
    noise = _single_source(density.inputs["Value"])
    separate = _single_source(horizon.inputs["Value"])
    coord_noise = _single_source(noise.inputs["Vector"])
    coord_height = _single_source(separate.inputs[0])
    if coord_noise != coord_height or coord_noise.type != "TEX_COORD":
        raise ValueError("Original sky coordinate contract changed")
    return {
        "background": background,
        "ramp": ramp,
        "noise": noise,
        "density": density,
        "horizon": horizon,
        "coordinate": coord_noise,
    }


def _record(world, nodes):
    return {
        "world": world.name,
        "strength": float(nodes["background"].inputs["Strength"].default_value),
        "ramp": [
            {"position": e.position, "rgba": list(e.color)}
            for e in nodes["ramp"].color_ramp.elements
        ],
        "noise": {
            key: float(nodes["noise"].inputs[key].default_value)
            for key in ("Scale", "Detail", "Roughness", "Distortion")
        },
        "density": {
            key: float(nodes["density"].inputs[key].default_value)
            for key in ("From Min", "From Max", "To Min", "To Max")
        },
        "horizon": {
            key: float(nodes["horizon"].inputs[key].default_value)
            for key in ("From Min", "From Max", "To Min", "To Max")
        },
        "coordinate_output": nodes["noise"].inputs["Vector"].links[0].from_socket.name,
        "density_interpolation": nodes["density"].interpolation_type,
        "horizon_interpolation": nodes["horizon"].interpolation_type,
    }


def set_enabled(scene, enabled):
    """Switch World pointers; the original World graph remains untouched."""
    if not isinstance(enabled, bool):
        raise TypeError("Daylight sky enabled must be boolean")
    if STATE not in scene:
        raise ValueError("Daylight sky is not installed in this scene")
    state = json.loads(scene[STATE])
    original = bpy.data.worlds.get(state["original_world"])
    daylight = bpy.data.worlds.get(state["daylight_world"])
    if original is None or daylight is None:
        raise ValueError("A retained daylight/original World is missing")
    if scene.world not in {original, daylight}:
        raise ValueError("Scene World changed outside the daylight sky module")
    scene.world = daylight if enabled else original
    state["enabled"] = enabled
    scene[STATE] = json.dumps(state, ensure_ascii=False)
    return {"enabled": enabled, "active_world": scene.world.name}


def remove(scene):
    """Restore original World and remove only the unused module-owned copy."""
    if STATE not in scene:
        return None
    state = json.loads(scene[STATE])
    set_enabled(scene, False)
    daylight = bpy.data.worlds[state["daylight_world"]]
    removed = daylight.users == 0
    if removed:
        bpy.data.worlds.remove(daylight)
    del scene[STATE]
    return {"active_world": scene.world.name, "daylight_copy_removed": removed}


def apply(scene, settings=None):
    """Copy and relight only the known procedural World; return a JSON report."""
    spec = _settings(settings)
    if STATE in scene:
        raise ValueError("Refusing repeated daylight sky installation")
    source = Path(bpy.data.filepath)
    if spec["verify_source_hash"]:
        with source.open("rb") as stream:
            if hashlib.file_digest(stream, "sha256").hexdigest() != SOURCE_SHA256:
                raise ValueError("Daylight sky requires the pinned Clean v2 source")
    original = scene.world
    if not original or original.name != EXPECTED_WORLD:
        raise ValueError("Daylight sky requires the known duet procedural World")
    before = _record(original, _contract(original))
    world = original.copy()
    world.name = PREFIX + "blue sky and soft clouds"
    world.use_fake_user = False
    try:
        nodes = _contract(world)
        nodes["background"].inputs["Strength"].default_value = spec["world_strength"]
        for element, color in zip(
            nodes["ramp"].color_ramp.elements, (spec["sky_blue"], spec["sky_cloud"])
        ):
            element.color = color
        for key, setting in (
            ("Scale", "noise_scale"),
            ("Detail", "noise_detail"),
            ("Roughness", "noise_roughness"),
            ("Distortion", "noise_distortion"),
        ):
            nodes["noise"].inputs[key].default_value = spec[setting]
        for key, settings_key in (
            ("density", "cloud_density_range"),
            ("horizon", "cloud_height_range"),
        ):
            node = nodes[key]
            node.clamp, node.interpolation_type = True, "SMOOTHSTEP"
            (
                node.inputs["From Min"].default_value,
                node.inputs["From Max"].default_value,
            ) = spec[settings_key]
        state = {
            "id": spec["id"],
            "original_world": original.name,
            "daylight_world": world.name,
            "enabled": spec["enabled"],
        }
        scene[STATE] = json.dumps(state, ensure_ascii=False)
        set_enabled(scene, spec["enabled"])
        after = _record(world, nodes)
        assert before == _record(original, _contract(original)), (
            "Original World changed"
        )
    except Exception:
        scene.world = original
        if STATE in scene:
            del scene[STATE]
        if world.users == 0:
            bpy.data.worlds.remove(world)
        raise
    return {
        "id": spec["id"],
        "settings": spec,
        "source_sha256": SOURCE_SHA256,
        "source": str(source),
        "before": before,
        "daylight": after,
        "active_world": scene.world.name,
        "sky_source": "Existing procedural World from hesperides_reference_rebuild.world_sky; no sky geometry or environment image",
        "spatial_motes_unchanged": [
            {"object": name, "hide_render": scene.objects[name].hide_render}
            for name in MOTES
            if name in scene.objects
        ],
        "no_new_images_downloads_or_sky_mesh": True,
        "actor_stage_materials_camera_lights_compositor_actions_unchanged": True,
        "original_world_unchanged": True,
        "probes_rebaked": False,
        "saved": False,
        "rendered": False,
        "limits": [
            "World blue/cloud changes only; independent spatial mote meshes are not stars in this World and are left for the caller to control",
            "Uses the existing proven sky coordinate graph; no original-author sky/lighting project was available",
            "No image has been rendered by this module; window cloud placement and exposure require visual review",
            "EEVEE cached probe lighting is inherited until the caller explicitly rebuilds it; this is not a new GI validation",
        ],
    }
