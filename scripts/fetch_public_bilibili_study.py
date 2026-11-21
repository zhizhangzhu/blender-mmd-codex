"""Retrieve normally accessible public tutorial metadata/media for private study.

No browser identity, cookies, login tokens or paid streams are used. A denied
endpoint is recorded as unavailable. Signed playback URLs stay in the temp dir.
"""

import argparse
import json
import urllib.parse
import urllib.request
from pathlib import Path

HEADERS = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.bilibili.com/"}


def request(url):
    return urllib.request.urlopen(
        urllib.request.Request(url, headers=HEADERS), timeout=25
    )


def get_json(url):
    with request(url) as response:
        return json.load(response)


def download(url, output):
    with request(url) as response, output.open("xb") as stream:
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            stream.write(chunk)
    print("PUBLIC_STUDY_MEDIA", output.name, output.stat().st_size, flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bvid", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=False)
    metadata = get_json(
        "https://api.bilibili.com/x/web-interface/view?"
        + urllib.parse.urlencode({"bvid": args.bvid})
    )
    (args.output_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    assert metadata.get("code") == 0, metadata.get("message")
    data = metadata["data"]
    cid, aid = data["pages"][0]["cid"], data["aid"]
    print(
        "PUBLIC_TUTORIAL",
        data["title"],
        data["owner"]["name"],
        cid,
        data["duration"],
        flush=True,
    )
    try:
        player = get_json(
            "https://api.bilibili.com/x/player/v2?"
            + urllib.parse.urlencode({"aid": aid, "cid": cid})
        )
        (args.output_dir / "player.json").write_text(
            json.dumps(player, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        subtitles = player.get("data", {}).get("subtitle", {}).get("subtitles", [])
        for i, subtitle in enumerate(subtitles):
            url = subtitle.get("subtitle_url")
            if url:
                download(
                    "https:" + url if url.startswith("//") else url,
                    args.output_dir / f"platform-subtitle-{i}.json",
                )
        print("PUBLIC_SUBTITLE_TRACKS", len(subtitles), flush=True)
    except (OSError, ValueError) as error:
        print(
            "PUBLIC_SUBTITLE_UNAVAILABLE", type(error).__name__, str(error), flush=True
        )
    playback = get_json(
        "https://api.bilibili.com/x/player/playurl?"
        + urllib.parse.urlencode(
            {"avid": aid, "cid": cid, "qn": 16, "fnval": 4048, "fourk": 0}
        )
    )
    (args.output_dir / "public-playback.json").write_text(
        json.dumps(playback, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    assert playback.get("code") == 0, playback.get("message")
    dash = playback.get("data", {}).get("dash")
    if dash:
        audio = min(dash["audio"], key=lambda a: a.get("bandwidth", 0))
        videos = [v for v in dash["video"] if v.get("codecs", "").startswith("avc")]
        video = min(
            videos or dash["video"],
            key=lambda v: (v.get("height", 0), v.get("bandwidth", 0)),
        )
        download(
            audio.get("baseUrl", audio.get("base_url")),
            args.output_dir / "tutorial-audio.m4s",
        )
        download(
            video.get("baseUrl", video.get("base_url")),
            args.output_dir / "tutorial-video.m4s",
        )
    else:
        urls = playback.get("data", {}).get("durl", [])
        if not urls:
            raise RuntimeError("No anonymous public stream available")
        download(urls[0]["url"], args.output_dir / "tutorial-public.mp4")


if __name__ == "__main__":
    main()
