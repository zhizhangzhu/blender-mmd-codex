"""Aspect-aware graphic post effects using real Blender character mattes.

No model recolor, text movement, frame-random noise or recovered PV Kit assets.
Procedural graphics use normalized image coordinates; widths use frame height.
"""

import cv2
import numpy as np


def graphic_background(h, w, seconds, settings):
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    u, v = xx / h, yy / h
    mode = settings["mode"]
    colors = [np.asarray(c, np.float32) for c in settings["colors"]]
    if mode == "argyle":
        # Diamond pattern in square image coordinates, not stretched by aspect.
        period = settings["period_height"]
        checker = (np.floor((u + v) / period) + np.floor((u - v) / period)) % 2
        image = np.where(checker[..., None] > 0, colors[0], colors[1])
    else:
        center = np.sqrt(((xx / w - 0.5) * 1.2) ** 2 + (yy / h - 0.45) ** 2)
        weight = np.clip(center, 0, 1)[..., None]
        image = colors[0] * (1 - weight) + colors[1] * weight
    image = image.copy()
    # Repeatable slow particles; deterministic phase in seconds, not frame IDs.
    for i in range(settings.get("particles", 0)):
        x = ((i * 0.61803398875 + 0.03 * np.sin(seconds * 0.7 + i)) % 1) * w
        y = ((i * 0.41421356237 - seconds * 0.018) % 1) * h
        radius = max(1, round(h * (0.0015 + 0.0004 * (i % 3))))
        cv2.circle(
            image,
            (round(x), round(y)),
            radius,
            tuple(settings["accent"]),
            -1,
            cv2.LINE_AA,
        )
    return image


def apply_post(rgb, actor, face, seconds, recipe):
    """Input/output sRGB [0,1]; comp uses linear color for the subject cutout."""
    try:
        from .typography_composite import srgb_to_linear, linear_to_srgb
    except ImportError:
        from typography_composite import srgb_to_linear, linear_to_srgb

    post, layout = recipe["post"], recipe["layout"]
    h, w = rgb.shape[:2]
    actual = "portrait" if h > w else "landscape"
    if actual != recipe["aspect"]:
        raise ValueError("Post recipe does not match the picture aspect")
    mask = np.clip(actor, 0, 1)
    result = rgb.copy()
    # Only modest color separation; face uses a weaker influence.
    grade = post["grade"]
    tint = np.asarray(grade["rgb_gain"], np.float32)
    graded = np.clip(result * tint, 0, 1)
    luma = graded @ np.asarray([0.2126, 0.7152, 0.0722], np.float32)
    graded = np.clip(
        luma[..., None] + (graded - luma[..., None]) * grade["saturation"], 0, 1
    )
    amount = grade["mix"] * (1 - np.clip(face, 0, 1) * 0.65)
    result = result * (1 - amount[..., None]) + graded * amount[..., None]
    bg = post["background"]
    if bg["mode"] == "argyle":
        background = graphic_background(h, w, seconds, bg)
        radius = max(1, round(layout["sticker_width_height"] * h))
        kernel = cv2.getStructuringElement(
            cv2.MORPH_ELLIPSE, (2 * radius + 1, 2 * radius + 1)
        )
        expanded = cv2.dilate(mask, kernel)
        outline = np.clip(expanded - mask, 0, 1)
        color = np.asarray(post["sticker_rgb"], np.float32)
        background = background * (1 - outline[..., None]) + color * outline[..., None]
        result = linear_to_srgb(
            srgb_to_linear(background) * (1 - mask[..., None])
            + srgb_to_linear(result) * mask[..., None]
        )
    elif bg["mode"] == "neon":
        overlay = graphic_background(h, w, seconds, bg)
        weight = (1 - mask) * bg["mix"]
        result = result * (1 - weight[..., None]) + overlay * weight[..., None]
    vignette = post.get("vignette", 0)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    falloff = np.clip(((xx / w - 0.5) ** 2 + (yy / h - 0.5) ** 2) * 2, 0, 1)
    result *= (1 - falloff * vignette * (1 - mask * 0.85))[..., None]
    if layout["border_height"] > 0:
        # Deliberate foreground frame; inset and width independent per aspect.
        inset = round(layout["border_inset_height"] * h)
        width = max(1, round(layout["border_height"] * h))
        cv2.rectangle(
            result,
            (inset, inset),
            (w - inset - 1, h - inset - 1),
            tuple(post["border_rgb"]),
            width,
            cv2.LINE_AA,
        )
    return np.clip(result, 0, 1)
