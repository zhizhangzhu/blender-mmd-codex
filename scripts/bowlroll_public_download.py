"""Download an author-published BowlRoll package only when open and password-free.

Uses the page's ordinary anonymous download form. Stops on password, login,
expired, or other restrictions; never guesses a password. Extracts data only.
"""

from __future__ import annotations

import argparse
import hashlib
import http.cookiejar
import io
import json
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import quote, urlencode, urlsplit, urlunsplit
from urllib.request import HTTPCookieProcessor, Request, build_opener
from zipfile import ZipFile


class DownloadPage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.data = {}

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id") == "initialize":
            self.data = values


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file-id", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--max-download-mb",
        type=int,
        default=2,
        help="Explicit package limit; larger stage assets need a deliberate override",
    )
    parser.add_argument("--max-extracted-mb", type=int, default=20)
    args = parser.parse_args()
    if not 1 <= args.max_download_mb <= 512 or not 1 <= args.max_extracted_mb <= 2048:
        raise ValueError("Invalid package size limit")
    download_limit = args.max_download_mb * 1_000_000
    if args.output_dir.exists():
        raise FileExistsError(args.output_dir)
    page_url = f"https://bowlroll.net/file/{args.file_id}"
    opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    headers = {"User-Agent": "Mozilla/5.0"}
    with opener.open(Request(page_url, headers=headers), timeout=25) as response:
        page = response.read().decode("utf-8")
    parsed = DownloadPage()
    parsed.feed(page)
    settings = parsed.data
    if (
        settings.get("data-download_control") != "permission"
        or settings.get("data-download_key") != "false"
    ):
        raise RuntimeError(
            "Not an open password-free download; use author's published access instructions"
        )
    form = urlencode(
        {
            "download_key": "bowlroll_download_control_mischievous",
            "csrf_token": settings["data-csrf_token"],
        }
    ).encode()
    request = Request(
        f"https://bowlroll.net/api/file/{args.file_id}/download-check",
        data=form,
        headers={
            **headers,
            "Referer": page_url,
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    with opener.open(request, timeout=25) as response:
        result = json.load(response)
    if result.get("status") != "success":
        raise RuntimeError("Author's ordinary download form did not grant access")
    parts = urlsplit(result["url"])
    if parts.scheme != "https":
        raise ValueError("Expected HTTPS download")
    # Public storage URLs can include literal Japanese filenames.
    url = urlunsplit(
        (
            parts.scheme,
            parts.netloc,
            quote(parts.path, safe="/%:@"),
            quote(parts.query, safe="=&%+/:;,"),
            "",
        )
    )
    with opener.open(
        Request(url, headers={**headers, "Referer": page_url}), timeout=30
    ) as response:
        raw = response.read(download_limit + 1)
    if len(raw) > download_limit:
        raise ValueError("Package exceeds the selected download limit")
    output = args.output_dir.resolve()
    root = output / "extracted"
    entries = []
    with ZipFile(io.BytesIO(raw)) as archive:
        if (
            sum(info.file_size for info in archive.infolist())
            > args.max_extracted_mb * 1_000_000
        ):
            raise ValueError("Uncompressed package exceeds limit")
        for info in archive.infolist():
            name = info.filename
            if not info.flag_bits & 0x800:
                try:
                    name = name.encode("cp437").decode("cp932")
                except UnicodeError:
                    pass
            target = (root / name).resolve()
            if (
                root not in target.parents
                or (info.external_attr >> 16) & 0o170000 == 0o120000
            ):
                raise ValueError("Unsafe ZIP entry")
            entries.append((info, target))
        output.mkdir(parents=True, exist_ok=False)
        (output / "original-camera-package.zip").write_bytes(raw)
        for info, target in entries:
            if info.is_dir():
                target.mkdir(parents=True, exist_ok=True)
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.read(info))
    report = {
        "author": settings.get("data-user_name"),
        "source_page": page_url,
        "sha256": hashlib.sha256(raw).hexdigest(),
        "bytes": len(raw),
        "files": [str(target.relative_to(output)) for _, target in entries],
        "download_method": "Anonymous public download form; no password required",
    }
    (output / "source.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
