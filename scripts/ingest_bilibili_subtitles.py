"""Normalize a legally saved Bilibili subtitle JSON, entirely offline.

No browser, cookies, network requests, JavaScript, or signed-URL downloads are
used. All transcript products go to an explicit, new directory outside this
repository. Obtaining a body array does not establish transcript completeness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
BODY_PATHS = (
    ("body",),
    ("data", "body"),
    ("subtitle", "body"),
    ("data", "subtitle", "body"),
)


class SubtitleInputError(ValueError):
    """The saved file cannot be converted without guessing or dropping cues."""


class ManifestOnlyError(SubtitleInputError):
    """Subtitle URL metadata was supplied rather than subtitle text."""


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise SubtitleInputError("JSON contains a duplicate object key")
        result[key] = value
    return result


def _has_subtitle_urls(value: Any) -> bool:
    if isinstance(value, dict):
        if isinstance(value.get("subtitle_url"), str):
            return True
        return any(_has_subtitle_urls(child) for child in value.values())
    if isinstance(value, list):
        return any(_has_subtitle_urls(child) for child in value)
    return isinstance(value, str) and value.startswith(("https://", "http://", "//"))


def extract_body(document: Any) -> tuple[list[Any], str]:
    """Use only documented containers; never search arbitrary objects for cues."""
    if isinstance(document, list):
        body, location = document, "$"
    else:
        candidates = []
        for path in BODY_PATHS:
            current = document
            for part in path:
                if not isinstance(current, dict) or part not in current:
                    break
                current = current[part]
            else:
                candidates.append((current, "$." + ".".join(path)))
        if len(candidates) > 1:
            raise SubtitleInputError(
                "Multiple supported body containers; save one track separately"
            )
        if not candidates:
            if _has_subtitle_urls(document):
                raise ManifestOnlyError(
                    "URL manifest supplied; no subtitle body was obtained"
                )
            raise SubtitleInputError(
                "No supported subtitle body: expected an array, body, data.body, subtitle.body, or data.subtitle.body"
            )
        body, location = candidates[0]
    if not isinstance(body, list):
        raise SubtitleInputError(f"{location} must be an array")
    if not body:
        raise SubtitleInputError(f"{location} is empty; no transcript can be asserted")
    if _has_subtitle_urls(body) and all(
        not isinstance(item, dict)
        or not any(key in item for key in ("from", "to", "content"))
        for item in body
    ):
        raise ManifestOnlyError("URL manifest supplied; no subtitle body was obtained")
    return body, location


def _valid_time(value: Any) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value) and value >= 0
    except OverflowError:
        return False


def normalize_cues(body: list[Any]) -> list[dict[str, Any]]:
    cues, errors = [], []
    for index, row in enumerate(body, 1):
        prefix = f"cue {index}"
        if not isinstance(row, dict):
            errors.append(f"{prefix} must be an object")
            continue
        start, end, content = row.get("from"), row.get("to"), row.get("content")
        valid_start, valid_end = _valid_time(start), _valid_time(end)
        if not valid_start:
            errors.append(f"{prefix}.from must be a finite nonnegative JSON number")
        if not valid_end:
            errors.append(f"{prefix}.to must be a finite nonnegative JSON number")
        if valid_start and valid_end and end <= start:
            errors.append(f"{prefix}.to must be greater than .from")
        if not isinstance(content, str):
            errors.append(f"{prefix}.content must be a string")
        # Do not trim, deduplicate, sort, correct ASR, or copy unrelated metadata.
        cues.append({"from": start, "to": end, "content": content})
    if errors:
        shown = "; ".join(errors[:20])
        suffix = f"; {len(errors) - 20} more errors" if len(errors) > 20 else ""
        raise SubtitleInputError(shown + suffix + "; no cues were exported")
    return cues


def _milliseconds(seconds: float) -> int:
    return int((Decimal(str(seconds)) * 1000).to_integral_value(rounding=ROUND_HALF_UP))


def _timestamp(milliseconds: int, separator: str = ",") -> str:
    seconds, millis = divmod(milliseconds, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}{separator}{millis:03d}"


def srt_text(cues: list[dict[str, Any]]) -> tuple[str, list[int]]:
    blocks, extended = [], []
    for index, cue in enumerate(cues, 1):
        start, end = _milliseconds(cue["from"]), _milliseconds(cue["to"])
        if end <= start:
            end = start + 1
            extended.append(index)
        # SRT is a display export; exact original text remains in normalized JSON.
        content = cue["content"].replace("\r\n", "\n").replace("\r", "\n")
        blocks.append(
            f"{index}\n{_timestamp(start)} --> {_timestamp(end)}\n{content}\n"
        )
    return "\n".join(blocks), extended


def markdown_text(cues: list[dict[str, Any]], source: dict[str, Any]) -> str:
    lines = [
        "# 本地字幕时间码",
        "",
        "完整性与识别准确率尚未核实；顺序、重复条和识别原文保留。",
        "",
        f"原输入 SHA-256：`{source['input_sha256']}`",
        "",
    ]
    if source.get("video_page_url"):
        lines.extend([f"来源视频：<{source['video_page_url']}>", ""])
    for index, cue in enumerate(cues, 1):
        start, end = (
            _timestamp(_milliseconds(cue["from"]), "."),
            _timestamp(_milliseconds(cue["to"]), "."),
        )
        # A fence longer than every input backtick run keeps subtitle text inert.
        fence = "`" * max(
            3,
            max((len(run) + 1 for run in re.findall(r"`+", cue["content"])), default=3),
        )
        lines.extend(
            [
                f"## {index} · {start} → {end}",
                "",
                fence + "text",
                cue["content"],
                fence,
                "",
            ]
        )
    return "\n".join(lines)


def subtitle_statistics(
    cues: list[dict[str, Any]], expected_duration: float | None = None
) -> dict[str, Any]:
    ordered = sorted(enumerate(cues, 1), key=lambda item: (item[1]["from"], item[0]))
    minimum = ordered[0][1]["from"]
    maximum, frontier_owner = ordered[0][1]["to"], ordered[0][0]
    covered, gaps, overlaps = maximum - minimum, [], []
    for index, cue in ordered[1:]:
        start, end = cue["from"], cue["to"]
        if start > maximum:
            gaps.append({"from": maximum, "to": start, "seconds": start - maximum})
        elif start < maximum:
            overlaps.append(
                {
                    "input_index": index,
                    "against_input_index": frontier_owner,
                    "from": start,
                    "to": min(end, maximum),
                }
            )
        covered += max(0, end - max(start, maximum))
        if end > maximum:
            maximum, frontier_owner = end, index
    duplicates: dict[tuple[Any, Any, str], list[int]] = defaultdict(list)
    for index, cue in enumerate(cues, 1):
        duplicates[(cue["from"], cue["to"], cue["content"])].append(index)
    result = {
        "input_cue_count": len(cues),
        "output_cue_count": len(cues),
        "text_codepoint_count": sum(len(cue["content"]) for cue in cues),
        "input_first_start_seconds": cues[0]["from"],
        "input_last_end_seconds": cues[-1]["to"],
        "minimum_start_seconds": minimum,
        "maximum_end_seconds": maximum,
        "initial_gap_from_zero_seconds": minimum,
        "covered_seconds": covered,
        "coverage_span_seconds": maximum - minimum,
        "internal_gap_count": len(gaps),
        "internal_gap_seconds": sum(gap["seconds"] for gap in gaps),
        "internal_gaps": gaps,
        "start_regression_input_indices": [
            index
            for index in range(2, len(cues) + 1)
            if cues[index - 1]["from"] < cues[index - 2]["from"]
        ],
        "overlap_witness_count": len(overlaps),
        "overlap_witnesses": overlaps,
        "overlap_policy": "One witness for each sorted cue overlapping prior coverage, against the earlier cue with the farthest end; not an exhaustive pair list. Touching boundaries are not overlaps.",
        "exact_duplicate_groups": [
            indices for indices in duplicates.values() if len(indices) > 1
        ],
        "whitespace_only_content_indices": [
            i for i, cue in enumerate(cues, 1) if not cue["content"].strip()
        ],
        "srt_content_with_blank_lines_indices": [
            i
            for i, cue in enumerate(cues, 1)
            if re.search(
                r"\n[ \t]*\n", cue["content"].replace("\r\n", "\n").replace("\r", "\n")
            )
        ],
        "completeness": "unassessed",
        "completeness_note": "A body array, a first cue at zero, an end matching duration, or no gaps cannot establish that all speech was transcribed. Silence can create legitimate gaps. Compare the selected video part and track with playback.",
    }
    if expected_duration is not None:
        result.update(
            {
                "expected_duration_seconds": expected_duration,
                "trailing_gap_to_expected_seconds": max(0, expected_duration - maximum),
                "end_beyond_expected_seconds": max(0, maximum - expected_duration),
            }
        )
    return result


def _video_page_url(value: str | None) -> str | None:
    if value is None:
        return None
    try:
        parts = urlsplit(value)
        host = parts.hostname or ""
        pairs = parse_qsl(parts.query, keep_blank_values=True)
        valid = (
            parts.scheme == "https"
            and host in ("www.bilibili.com", "m.bilibili.com", "bilibili.com")
            and parts.username is None
            and parts.password is None
            and parts.port in (None, 443)
            and re.fullmatch(r"/video/(?:BV[0-9A-Za-z]+|av[0-9]+)/?", parts.path)
            and len(pairs) <= 1
            and all(
                key == "p" and re.fullmatch(r"[1-9][0-9]*", item) for key, item in pairs
            )
        )
    except ValueError:
        valid = False
    if not valid:
        raise SubtitleInputError(
            "source-url must be a public HTTPS Bilibili /video/ page; only the p part query is allowed, never a signed subtitle URL"
        )
    return urlunsplit(("https", host, parts.path, urlencode(pairs), ""))


def ingest_subtitles(
    input_path: Path | str,
    output_dir: Path | str,
    *,
    source_url: str | None = None,
    source_label: str | None = None,
    expected_duration: float | None = None,
) -> dict[str, Any]:
    """Validate everything before creating a new output directory; never overwrite."""
    requested_output = Path(output_dir).expanduser()
    if os.path.lexists(requested_output):
        raise FileExistsError(f"Output already exists: {requested_output}")
    output = requested_output.resolve()
    if output == REPOSITORY_ROOT or REPOSITORY_ROOT in output.parents:
        raise ValueError(
            "Full transcript products must be outside this repository, in an explicit output directory"
        )
    if expected_duration is not None and (
        not _valid_time(expected_duration) or expected_duration == 0
    ):
        raise SubtitleInputError("expected-duration must be a finite positive number")
    video_page = _video_page_url(source_url)
    input_path = Path(input_path)
    raw = input_path.read_bytes()
    try:
        document = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_object)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise SubtitleInputError(
            "Input must be a UTF-8 JSON file, not HTML, JavaScript, or a URL"
        ) from error
    body, body_path = extract_body(document)
    cues = normalize_cues(body)
    source = {
        "input_name": input_path.name,
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "body_path": body_path,
    }
    if video_page is not None:
        source["video_page_url"] = video_page
    if source_label is not None:
        source["label"] = source_label
    normalized = {"schema_version": 1, "source": source, "subtitles": cues}
    srt, extended = srt_text(cues)
    report = {
        "schema_version": 1,
        "source": source,
        "input_bytes": len(raw),
        "statistics": subtitle_statistics(cues, expected_duration),
        "preservation": {
            "input_order": True,
            "duplicates": True,
            "content_verbatim_in_json": True,
            "unrelated_input_metadata_copied": False,
        },
        "srt_export": {
            "rounding": "Nearest millisecond, halves up; only positive cues rounding to zero are extended to 1 ms.",
            "extended_to_one_millisecond_input_indices": extended,
            "text_policy": "CRLF/CR are normalized to LF; other text is preserved. Blank source lines can be ambiguous in SRT players; normalized JSON remains authoritative.",
        },
        "files": [
            "subtitles.normalized.json",
            "subtitles.srt",
            "subtitles.md",
            "report.json",
        ],
    }
    products = {
        "subtitles.normalized.json": json.dumps(
            normalized, ensure_ascii=False, indent=2, allow_nan=False
        )
        + "\n",
        "subtitles.srt": srt,
        "subtitles.md": markdown_text(cues, source),
        "report.json": json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False)
        + "\n",
    }
    try:
        encoded_products = {
            name: text.encode("utf-8") for name, text in products.items()
        }
    except UnicodeEncodeError as error:
        raise SubtitleInputError(
            "Unpaired Unicode surrogate cannot be preserved in UTF-8 output; no cues were exported"
        ) from error
    output.mkdir(parents=True, exist_ok=False)
    for name, content in encoded_products.items():
        # Exclusive creation also protects against an unexpected concurrent writer.
        with (output / name).open("xb") as handle:
            handle.write(content)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Legally saved UTF-8 subtitle body JSON",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        required=True,
        help="New directory outside the repository; no overwrite option",
    )
    parser.add_argument(
        "--source-url", help="Public Bilibili video page; optional p part query only"
    )
    parser.add_argument(
        "--source-label",
        help="Optional provenance label, e.g. AI字幕; does not establish accuracy",
    )
    parser.add_argument(
        "--expected-duration",
        type=float,
        help="Selected part duration in seconds, for comparison only",
    )
    args = parser.parse_args(argv)
    try:
        report = ingest_subtitles(
            args.input,
            args.output_dir,
            source_url=args.source_url,
            source_label=args.source_label,
            expected_duration=args.expected_duration,
        )
    except (OSError, ValueError) as error:
        parser.error(str(error))
    # Keep transcript text out of tool logs; read the generated products explicitly.
    print(
        json.dumps(
            {
                "output_dir": str(args.output_dir.resolve()),
                "cue_count": report["statistics"]["output_cue_count"],
                "input_sha256": report["source"]["input_sha256"],
                "completeness": "unassessed",
                "files": report["files"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
