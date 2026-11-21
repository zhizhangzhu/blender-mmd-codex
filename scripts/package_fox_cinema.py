"""Publish only the verified five-second cinema study and its real comparisons."""

import argparse
import hashlib
import json
import shutil
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

REPO = Path(__file__).resolve().parents[1]


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def frame(path, index, output):
    cap = cv2.VideoCapture(str(path))
    cap.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, pixels = cap.read()
    cap.release()
    assert ok
    cv2.imencode(".png", pixels)[1].tofile(str(output))
    return output


def panel(items, destination, width=800):
    images = [Image.open(path).convert("RGB") for path, _ in items]
    height = round(width * images[0].height / images[0].width)
    canvas = Image.new("RGB", (width * len(items), height + 55), "#131827")
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 21)
    for i, ((_, text), image) in enumerate(zip(items, images)):
        canvas.paste(
            image.resize((width, height), Image.Resampling.LANCZOS), (i * width, 55)
        )
        draw.text((i * width + 12, 13), text, font=font, fill="white")
    canvas.save(destination, quality=95)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    prod = root / "production-v2"
    sample = root / "sample-5s-v1"
    video = read(sample / "video-qa/video-verification.json")
    audio = read(sample / "audio-verification.json")
    seam = read(sample / "seam-qa/seam-verification.json")
    study = read(prod / "cinema-study.json")
    assert all(x["passed"] for x in (video, audio, seam))
    assert video["decoded_frames"] == 300
    assert all(
        x["rig_camera_and_lens_exactly_equal"] for x in study["source_motion_checks"]
    )
    reopened = read(root / "reopened-scene-probe.json")
    assert reopened["render"]["use_motion_blur"] == "True"
    assert all(
        abs(float(c["dof"]["aperture_fstop"]) - 2.8) < 0.00001
        and c["dof"]["focus_object"] == "None"
        for c in reopened["camera"].values()
    )
    review = root / "review"
    review.mkdir(exist_ok=True)
    previous = Path(
        "D:/codex/output/MMD-Quality-Integration-v1/sample-5s-v2/Aether_Duet_5s_REVIEW.mp4"
    )
    movie = sample / "Aether_Duet_5s_REVIEW.mp4"
    before = frame(previous, 60, review / "before-4200.png")
    after = frame(movie, 60, review / "after-4200.png")
    panel(
        [(before, "前版：均匀明亮礼堂"), (after, "新版：冷夜建筑＋暖色走道＋景深")],
        review / "before-after.jpg",
    )
    panel(
        [
            (prod / "01-baseline.png", "同帧原基线"),
            (prod / "02-lighting-only.png", "只改变舞台与受光"),
            (prod / "03-lighting-focus.png", "再加入双人景深"),
        ],
        review / "lighting-focus-breakdown.jpg",
        640,
    )
    panel(
        [
            (prod / "control-motion-off-4290.png", "同帧：运动模糊关"),
            (prod / "04-lighting-focus-motion.png", "同帧：0.35 帧原生快门"),
        ],
        review / "motion-toggle.jpg",
    )
    panel(
        [
            (prod / "lens-35mm-matched-framing.png", "35 mm：近似同景别、机位更近"),
            (prod / "lens-85mm-matched-framing.png", "85 mm：退远机位、背景比例更大"),
        ],
        review / "lens-comparison.jpg",
    )

    def pixels(name):
        return np.asarray(Image.open(prod / name).convert("RGB"), dtype=np.float32)

    base = pixels("01-baseline.png")
    light = pixels("02-lighting-only.png")
    focus = pixels("03-lighting-focus.png")
    off = pixels("control-motion-off-4290.png")
    on = pixels("04-lighting-focus-motion.png")
    measurements = {
        "units": "Mean absolute RGB difference on decoded 8-bit stills, not a quality score",
        "lighting_mae": float(abs(base - light).mean()),
        "dof_mae": float(abs(focus - light).mean()),
        "same_frame_motion_mae": float(abs(on - off).mean()),
    }
    assert (
        measurements["lighting_mae"] > 5
        and measurements["dof_mae"] > 0.05
        and measurements["same_frame_motion_mae"] > 0.05
    )
    write(review / "effect-controls.json", measurements)
    write(
        review / "manual-review.json",
        {
            "reviewer": "Codex",
            "user_art_approval": False,
            "inspected": [
                "24 reference overview frames and five consecutive 12-frame reference groups",
                "12 final movie representative frames",
                "render chunk seam frames 148..152",
                "same-frame lighting/DOF/motion and matched-framing lens comparisons",
            ],
            "observations": [
                "Deep blue windows replace daytime cyan; warmer aisle and darker architecture separate the readable characters",
                "Both faces remain readable in inspected samples; fast hands and moving heads can soften under the native shutter",
                "Background focus varies with the unchanged authored camera; full-song optics and portrait composition remain unverified",
            ],
            "limitations": [
                "Not the reference author's camera, lights or original MME",
                "Not proof of no artifacts in every intermediate frame",
                "NPR light pools and added rims have no physical occlusion",
            ],
        },
    )
    recipe = {
        "id": "hesperides-fox-cinema-v1",
        "status": "verified-5-second-study",
        "user_art_approval": False,
        "engine": "Blender 5.2.2 EEVEE",
        "input": study["source"],
        "project": study["project"],
        "preset": "presets/stages/hesperides-fox-cinema-v1.json",
        "frame_range": [4140, 4439],
        "resolution": [1920, 1080],
        "fps": 60,
        "video": str(movie),
        "focus": {
            "minimum_fstop": 2.8,
            "maximum_predicted_head_coc_pixels": study["optics"][
                "maximum_predicted_head_coc_pixels"
            ],
        },
        "motion": study["settings"]["motion"],
        "cuts": study["optics"]["cut_protection_frames"],
        "native_exr_export": False,
        "limits": study["settings"]["limits"],
    }
    write(REPO / "presets/recipes/hesperides-fox-cinema-v1.json", recipe)
    catalog_path = REPO / "catalog/library.json"
    catalog = read(catalog_path)
    entry = {
        "id": "hesperides-fox-cinema-v1",
        "title": "夜誓 · 灯光与镜头",
        "collection": "FOX STUDY / CINEMA",
        "subtitle": "参考小狐狸的舞台分离与光学层次，转成冷夜礼堂、暖色走道和双人景深。",
        "category": "stage",
        "family": "guanhaizi",
        "aspect": "landscape",
        "status": "motion",
        "image": str(after),
        "video": str(movie),
        "duration": 5,
        "fps": 60,
        "docs": ["FOX_LIGHTING_AND_CINEMA.md", "GUANHAIZI_REFERENCE.md"],
        "configs": [
            "presets/stages/hesperides-fox-cinema-v1.json",
            "presets/recipes/hesperides-fox-cinema-v1.json",
        ],
        "project": study["project"],
        "look": [
            "深蓝建筑与局部暖光",
            "明亮肤色与清楚脸线",
            "双人对焦与背景散景",
            "原生方向运动模糊",
        ],
        "evidence": [
            "300 帧 1080p60 原声样片与接缝验收通过",
            "同帧灯光／景深／运动模糊开关；35/85 mm 近似同景别对照",
            "原动作／相机／焦段五时点精确相等",
        ],
        "limits": [
            "参考后的本机方案，非作者原参数；等待猪猪美术评价",
            "仅五秒动态通过，双人全曲与竖屏尚未验收",
            "NPR 色池／补充亮边无物理遮挡；辅助 RGBA 场景未校准",
        ],
        "compatibility": "Blender 5.2.2 / EEVEE；固定双人和现成礼堂，原生景深与快门。",
        "command": f"python scripts/render_duet_sample.py --blend '{study['project']}' --output-dir 'D:\\codex\\output\\Fox-Cinema-New-Sample' --logs 'D:\\codex\\temp\\Fox-Cinema-New-Sample' --start 4140 --frames 300 --workers 2",
    }
    catalog["entries"] = [entry] + [
        e for e in catalog["entries"] if e["id"] != entry["id"]
    ]
    pairs = [
        {
            "id": "fox-cinema-lighting",
            "title": "明亮礼堂 / 夜誓灯光与景深",
            "subtitle": "两支真实动态样片的同一 4200 帧与原相机；人物光学效果也随新版调整。",
            "before_label": "前版明亮",
            "after_label": "新版夜誓",
            "before": str(before),
            "after": str(after),
            "doc": "FOX_LIGHTING_AND_CINEMA.md",
        },
        {
            "id": "fox-cinema-focus",
            "title": "同灯光 / f/10 与 f/2.8",
            "subtitle": "相同 4200 帧与灯光，比较较深与较浅景深；前版也开启了景深。",
            "before_label": "原 f/10",
            "after_label": "双人 f/2.8",
            "before": str(prod / "02-lighting-only.png"),
            "after": str(prod / "03-lighting-focus.png"),
            "doc": "FOX_LIGHTING_AND_CINEMA.md",
        },
        {
            "id": "fox-cinema-motion",
            "title": "同帧 / 运动模糊开关",
            "subtitle": "相同 4290 帧与景深；观察移动的手臂和轮廓。",
            "before_label": "快门关",
            "after_label": "0.35 帧快门",
            "before": str(prod / "control-motion-off-4290.png"),
            "after": str(prod / "04-lighting-focus-motion.png"),
            "doc": "FOX_LIGHTING_AND_CINEMA.md",
        },
    ]
    catalog["comparisons"] = pairs + [
        p for p in catalog["comparisons"] if p["id"] not in {p["id"] for p in pairs}
    ]
    lens_pair = {
        "id": "fox-cinema-lens",
        "title": "近似同景别 / 35 mm 与 85 mm",
        "subtitle": "独立焦段实验，同时调整相机距离；不是正式视频的相机或原作者参数。",
        "before_label": "35 mm 较近机位",
        "after_label": "85 mm 退远机位",
        "before": str(prod / "lens-35mm-matched-framing.png"),
        "after": str(prod / "lens-85mm-matched-framing.png"),
        "doc": "FOX_LIGHTING_AND_CINEMA.md",
    }
    catalog["comparisons"] = [
        p for p in catalog["comparisons"] if p["id"] != lens_pair["id"]
    ] + [lens_pair]
    group = next(g for g in catalog["knowledge_groups"] if g["id"] == "lighting")
    group["docs"] = ["FOX_LIGHTING_AND_CINEMA.md"] + [
        d for d in group["docs"] if d != "FOX_LIGHTING_AND_CINEMA.md"
    ]
    write(catalog_path, catalog)
    credits = Path("D:/codex/output/MMD-Quality-Integration-v1")
    shutil.copyfile(credits / "CREDITS.md", root / "CREDITS.md")
    with (root / "CREDITS.md").open("a", encoding="utf-8") as stream:
        stream.write(
            "\n本轮灯光与光学视觉参考：观海子《亲亲小狐狸！露帕×女漂》，简介提及黑煤球的后期；本项目未使用其场景、模型、源工程或 MME，未恢复原作者参数。\nhttps://www.bilibili.com/video/BV1PPgpzLEdb/\n"
        )
    for source in (credits / "licenses").glob("*"):
        if source.is_file():
            (root / "licenses").mkdir(exist_ok=True)
            shutil.copyfile(source, root / "licenses" / source.name)
    shutil.copyfile(
        REPO / "docs/FOX_LIGHTING_AND_CINEMA.md", root / "FOX_LIGHTING_AND_CINEMA.md"
    )
    (root / "README.md").write_text(
        "# 夜誓 · 灯光与镜头五秒样片\n\n"
        + f"视频：`{movie}`\n\n工程：`{study['project']}`\n\n"
        + "参考观海子《亲亲小狐狸》的灯光层次、景深和运动模糊；转成雪夜礼堂方案，非原作者参数。1080p60、300 原生帧及指定原声 FLAC 混流验收通过。旧版保留，等待猪猪美术评价。\n\n`review` 内有前后对照、灯光／景深拆解、同帧运动模糊开关和 35／85 mm 对照。使用范围为原帧 4140–4439，未完成全曲。完整记录见 FOX_LIGHTING_AND_CINEMA.md。\n",
        encoding="utf-8",
    )
    write(
        root / "delivery.json",
        {
            "movie": str(movie),
            "movie_sha256": hashlib.sha256(movie.read_bytes()).hexdigest(),
            "project": study["project"],
            "video_verified": True,
            "audio_verified": True,
            "seam_verified": True,
            "frames": 300,
            "seconds": 5,
            "user_art_approval": False,
            "reference": study["settings"]["reference"],
            "effect_controls": measurements,
            "full_song_complete": False,
        },
    )
    print("FOX_CINEMA_PACKAGED", movie, flush=True)


if __name__ == "__main__":
    main()
