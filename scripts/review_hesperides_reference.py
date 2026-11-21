"""Package actual stage renders into labeled reference and switch comparisons."""

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def font(size):
    return ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", size)


def tile(canvas, path, x, y, width, label):
    img = (
        Image.open(path)
        .convert("RGB")
        .resize((width, round(width * 9 / 16)), Image.Resampling.LANCZOS)
    )
    canvas.paste(img, (x, y + 54))
    ImageDraw.Draw(canvas).text(
        (x + 16, y + 12), label, font=font(24), fill=(235, 240, 250)
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    args = parser.parse_args()
    out = args.root / "review"
    out.mkdir(parents=True, exist_ok=False)
    study = args.root / "final-study"
    final = study / "reference-rebuild.png"
    reopened = args.root / "reopen-verification/reopened.png"
    a = np.asarray(Image.open(final).convert("RGB"), dtype=float)
    b = np.asarray(Image.open(reopened).convert("RGB"), dtype=float)
    diff = np.abs(a - b)
    qa = json.loads(
        (args.root / "reopen-verification/verification.json").read_text(
            encoding="utf-8"
        )
    )
    comparison = Image.new("RGB", (2560, 774), (20, 27, 40))
    tile(comparison, args.reference, 0, 0, 1280, "作者 Ray 预览｜miHoYo / paierer")
    tile(comparison, final, 1280, 0, 1280, "本轮 Blender 重建｜估计机位，非原始工程")
    comparison.save(out / "reference-comparison.jpg", quality=95)
    switches = Image.new("RGB", (1920, 1188), (20, 27, 40))
    for index, (name, label) in enumerate(
        [
            ("reference-rebuild.png", "当前研究结果"),
            ("control-ordinary-pbr.png", "同条件：改回普通 PBR"),
            ("control-no-matcap.png", "同条件：关闭 MatCap"),
            ("control-no-grade.png", "同条件：关闭参考曲线"),
        ]
    ):
        tile(switches, study / name, (index % 2) * 960, (index // 2) * 594, 960, label)
    switches.save(out / "switch-comparison.jpg", quality=95)
    changes = {}
    for path in study.glob("control-*.png"):
        value = np.asarray(Image.open(path).convert("RGB"), dtype=float)
        changes[path.stem] = {
            "mean_absolute_difference_8bit": float(np.abs(a - value).mean())
        }
    report = {
        "settings_reopen_passed": qa["passed"],
        "reopen_mean_absolute_difference_8bit": float(diff.mean()),
        "reopen_max_difference_8bit": float(diff.max()),
        "reopen_p99_difference_8bit": float(np.percentile(diff, 99)),
        "image_size": [a.shape[1], a.shape[0]],
        "control_differences": changes,
        "artistic_acceptance": "pending user review; camera/cloth/highlights/sky still differ from supplied preview",
        "reference_comparison": "reference-comparison.jpg",
        "switch_comparison": "switch-comparison.jpg",
        "stage_project_sha256": hashlib.sha256(
            (study / "Hesperides_Reference_Rebuild.blend").read_bytes()
        ).hexdigest(),
    }
    report["reopen_pixels_passed"] = (
        report["reopen_mean_absolute_difference_8bit"] < 0.5
        and report["reopen_p99_difference_8bit"] <= 2
    )
    (out / "review-report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (args.root / "README.md").write_text(
        "# 礼堂 Ray 预览重建研究\n\n已输出 1920×1080 场景静帧、独立 Blender 工程、四组开关实验，并在另一进程重开、检查 56 张贴图打包和实际重渲。\n\n先看 review/reference-comparison.jpg（左：作者参考；右：Blender 重建），再看 review/switch-comparison.jpg。当前项目在 final-study/Hesperides_Reference_Rebuild.blend，主图 reference-rebuild.png。\n\n关键方法：随包 ToonBased 响应、14 份原强度加算 MatCap、白幔蓝紫副贴图、GGX 镜面、窗光与三类探针、背景参考曲线。各开关对照保持同样的机位与其余设置。\n\n局限：原作者灯光、天空盒及完整后期未取得，白幔硬折、局部亮斑、部分框架偏暖仍不同；光点尚未动画。本轮没有合回人物或输出新 MMD 视频，不是全曲成品或用户美术验收通过。\n\n模型 miHoYo，改造 paierer，Ray 材质 Rui_cg／三金络合物／paierer，限随包允许的非商业用途。\n\n复用方法：D:/codex/workspace/blender-mmd-codex/docs/HESPERIDES_REFERENCE_REBUILD.md；完整参数：final-study/rebuild-report.json。早期 study-v* 目录仅为过程记录。\n",
        encoding="utf-8",
    )
    print(json.dumps(report, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
