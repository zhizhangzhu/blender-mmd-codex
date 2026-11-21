"""Whole-group caption compositing with explicit layer order and continuous masks.

Black-backed video is not RGBA. Plate mode reconstructs an opaque card interior;
glyph mode preserves letter holes. This does not recover black artwork outside
the visible white card or provide exact three-layer beauty decomposition.
"""

import cv2
import numpy as np

try:
    from .typography_composite import linear_to_srgb, over, srgb_to_linear
except ImportError:
    from typography_composite import linear_to_srgb, over, srgb_to_linear


def validate(profile):
    required = profile["source_start_frame"]
    identities = set()
    for cue in profile["cues"]:
        if (
            cue["id"] in identities
            or cue["start_frame"] != required
            or cue["end_frame"] <= required
        ):
            raise ValueError(
                "Cue groups must be unique, contiguous and non-overlapping"
            )
        if cue["order"] not in {"front", "behind"} or cue["key_mode"] not in {
            "glyph",
            "plate",
            "mixed",
        }:
            raise ValueError("Unsupported complete-group policy")
        if cue.get("protect", "none") != "none":
            raise ValueError(
                "Front groups cannot be partially placed behind face/character masks"
            )
        if not 0 < cue["scale"] <= 2 or not 0 <= cue.get("opacity", 1) <= 1:
            raise ValueError("Invalid caption layout")
        required = cue["end_frame"]
        identities.add(cue["id"])
    if required != profile["source_start_frame"] + profile["render_frames"]:
        raise ValueError("Caption groups must cover the chosen source interval exactly")


def cue_at(profile, source_frame):
    return next(
        c for c in profile["cues"] if c["start_frame"] <= source_frame < c["end_frame"]
    )


def theme_field(shape, stops):
    """A deterministic source-space gradient; no actor or frame-dependent color."""
    height, width = shape
    positions = np.linspace(0, 1, len(stops))
    x = np.linspace(0, 1, width)
    columns = np.stack(
        [np.interp(x, positions, np.asarray(stops)[:, c]) for c in range(3)], axis=1
    )
    return np.broadcast_to(
        srgb_to_linear(columns.astype(np.float32))[None], (height, width, 3)
    )


def extract_layer(source_rgb, mode, tint, palette=None):
    brightness = source_rgb.max(axis=2)
    alpha = brightness.copy()
    if mode in {"plate", "mixed"}:
        binary = (brightness > 0.06).astype(np.uint8)
        contours, _ = cv2.findContours(
            binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        filled = np.zeros_like(binary)
        for contour in contours:
            area = cv2.contourArea(contour)
            _x, _y, w, h = cv2.boundingRect(contour)
            if mode == "mixed" and (
                area < source_rgb.shape[0] * source_rgb.shape[1] * 0.018
                or area / max(1, w * h) < 0.70
            ):
                continue
            cv2.drawContours(filled, [contour], -1, 1, cv2.FILLED)
        if mode == "plate" and contours:
            # Official black type can run all the way through a white card,
            # splitting it into several white components. Reconstruct the
            # whole convex card, rather than only filling enclosed letter holes.
            hull = cv2.convexHull(np.concatenate(contours, axis=0))
            cv2.drawContours(filled, [hull], -1, 1, cv2.FILLED)
        interior = cv2.erode(filled, np.ones((3, 3), np.uint8)).astype(np.float32)
        alpha = np.maximum(alpha, interior)
        unpremultiplied = np.divide(
            source_rgb,
            alpha[..., None],
            out=np.zeros_like(source_rgb),
            where=alpha[..., None] > 0.00001,
        )
        color = srgb_to_linear(
            np.clip(unpremultiplied * np.asarray(tint, np.float32), 0, 1)
        )
    elif mode == "glyph":
        color = srgb_to_linear(np.asarray(tint, np.float32))
    else:
        raise ValueError(mode)
    if palette:
        paper = theme_field(alpha.shape, palette["light_stops_srgb"])
        if mode == "glyph":
            color = paper
        else:
            ink = theme_field(alpha.shape, palette["dark_stops_srgb"])
            signal = np.divide(
                brightness, alpha, out=np.zeros_like(alpha), where=alpha > 0.00001
            )
            color = ink + np.clip(signal, 0, 1)[..., None] * (paper - ink)
    return color * alpha[..., None], alpha


def style_layer(premultiplied, alpha, profile):
    height, width = alpha.shape
    factor = height / 1080
    stroke = max(0, round(profile["stroke_pixels_at_1080"] * factor))
    expanded = (
        cv2.dilate(
            alpha,
            cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (stroke * 2 + 1, stroke * 2 + 1)
            ),
        )
        if stroke
        else alpha
    )
    dx, dy = [v * factor for v in profile["shadow_offset_pixels_at_1080"]]
    shadow = (
        cv2.warpAffine(
            expanded,
            np.float32([[1, 0, dx], [0, 1, dy]]),
            (width, height),
            flags=cv2.INTER_LINEAR,
            borderValue=0,
        )
        * profile["shadow_opacity"]
    )
    result = (
        srgb_to_linear(np.asarray(profile["shadow_srgb"], np.float32))
        * shadow[..., None]
    )
    total = shadow
    if profile.get("glow_strength", 0):
        sigma = profile["glow_sigma_pixels_at_1080"] * factor
        glow_alpha = cv2.GaussianBlur(alpha, (0, 0), sigma) * profile["glow_strength"]
        glow_color = (
            cv2.GaussianBlur(premultiplied, (0, 0), sigma) * profile["glow_strength"]
        )
        result = result * (1 - glow_alpha[..., None]) + glow_color
        total = total * (1 - glow_alpha) + glow_alpha
    if stroke:
        stroke_color = srgb_to_linear(np.asarray(profile["stroke_srgb"], np.float32))
        result = result * (1 - expanded[..., None]) + stroke_color * expanded[..., None]
        total = total * (1 - expanded) + expanded
    result = result * (1 - alpha[..., None]) + premultiplied
    total = total * (1 - alpha) + alpha
    return result, total


def layout_layer(premultiplied, alpha, cue):
    height, width = alpha.shape
    scale = cue["scale"]
    ox, oy = cue["offset"]
    matrix = np.float32(
        [
            [scale, 0, width * (0.5 - scale * 0.5 + ox)],
            [0, scale, height * (0.5 - scale * 0.5 + oy)],
        ]
    )
    color = cv2.warpAffine(
        premultiplied, matrix, (width, height), flags=cv2.INTER_LINEAR, borderValue=0
    )
    coverage = cv2.warpAffine(
        alpha, matrix, (width, height), flags=cv2.INTER_LINEAR, borderValue=0
    )
    opacity = cue.get("opacity", 1)
    return color * opacity, coverage * opacity


def continuous_actor_mask(mask, margin):
    mask = np.clip(mask.astype(np.float32), 0, 1)
    if margin:
        mask = cv2.dilate(
            mask,
            cv2.getStructuringElement(
                cv2.MORPH_ELLIPSE, (2 * margin + 1, 2 * margin + 1)
            ),
        )
    return mask


def composite(base_srgb, premultiplied, alpha, actor, order):
    if order == "behind":
        keep = 1 - actor
        premultiplied, alpha = premultiplied * keep[..., None], alpha * keep
    elif order != "front":
        raise ValueError(order)
    # Front is independent of every matte, including the face. Occlusion is an
    # editorial choice for the whole group, not a pixel-dependent order switch.
    return linear_to_srgb(over(srgb_to_linear(base_srgb), premultiplied, alpha))
