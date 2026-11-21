"""Explicit SDR desktop-review color contract for sRGB compositor pixels.

BT.709 primaries and YCbCr matrix, limited video range, sRGB transfer. This
preserves source display RGB values rather than relabeling them BT.709 TRC.
"""

CONTRACT = {
    "input": "Full-range display sRGB RGB24",
    "matrix": "bt709",
    "primaries": "bt709",
    "transfer": "iec61966-2-1",
    "range": "tv",
    "hdr": False,
    "meaning": "SDR PC-review output, preserving source sRGB transfer; not a Rec.709/BT.1886 grading master",
}


def encoder_arguments():
    return [
        "-vf",
        (
            "scale=in_range=pc:out_range=tv:out_color_matrix=bt709,format=yuv420p,"
            "setparams=range=limited:color_primaries=bt709:"
            "color_trc=iec61966-2-1:colorspace=bt709"
        ),
        "-color_range",
        "tv",
        "-colorspace",
        "bt709",
        "-color_primaries",
        "bt709",
        "-color_trc",
        "iec61966-2-1",
    ]
