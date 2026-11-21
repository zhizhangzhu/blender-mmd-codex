"""Create a private, timestamped ASR study draft from local tutorial media.

Requires sherpa-onnx and a SenseVoice model. Output is machine transcription,
not platform subtitles or a verified verbatim transcript. Keep copyrighted
tutorial drafts private; publish original learning notes instead.
"""

import argparse
import hashlib
import json
import re
import subprocess
import time
import wave
from pathlib import Path

import numpy as np
import sherpa_onnx


def stamp(seconds):
    milliseconds = round(seconds * 1000)
    hours, milliseconds = divmod(milliseconds, 3600000)
    minutes, milliseconds = divmod(milliseconds, 60000)
    seconds, milliseconds = divmod(milliseconds, 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{milliseconds:03}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--model-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--ffmpeg", type=Path, required=True)
    parser.add_argument("--start-seconds", type=float, default=0)
    parser.add_argument("--duration", type=float)
    parser.add_argument("--threads", type=int, default=4)
    parser.add_argument("--segment-seconds", type=float, default=20)
    args = parser.parse_args()
    if (
        args.threads < 1
        or not 5 <= args.segment_seconds <= 30
        or args.start_seconds < 0
    ):
        parser.error("Invalid threading, segmentation or start time")
    if not args.input.is_file():
        raise FileNotFoundError(args.input)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    decoded = args.output_dir / "speech-16k.wav"
    command = [str(args.ffmpeg), "-hide_banner", "-loglevel", "error"]
    if args.start_seconds:
        command += ["-ss", str(args.start_seconds)]
    command += [
        "-i",
        str(args.input),
        "-vn",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-c:a",
        "pcm_s16le",
    ]
    if args.duration:
        command += ["-t", str(args.duration)]
    command.append(str(decoded))
    subprocess.run(command, check=True)
    recognizer = sherpa_onnx.OfflineRecognizer.from_sense_voice(
        model=str(args.model_dir / "model.int8.onnx"),
        tokens=str(args.model_dir / "tokens.txt"),
        language="zh",
        use_itn=True,
        num_threads=args.threads,
        debug=False,
    )
    started = time.perf_counter()
    segments = []
    with (
        wave.open(str(decoded), "rb") as audio,
        (args.output_dir / "segments.jsonl").open("w", encoding="utf-8") as ledger,
    ):
        rate = audio.getframerate()
        assert audio.getnchannels() == 1 and audio.getsampwidth() == 2 and rate == 16000
        total = audio.getnframes()
        cursor = 0
        while cursor < total:
            audio.setpos(cursor)
            raw = audio.readframes(
                min(round(args.segment_seconds * rate), total - cursor)
            )
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768
            # Prefer a local quiet boundary in the last second; never overlap
            # windows, so repeated words are not silently deleted or duplicated.
            count = len(samples)
            if cursor + count < total and count > rate * 5:
                quiet = []
                for end in range(count - rate, count, rate // 25):
                    quiet.append(
                        (
                            float(
                                np.mean(samples[max(0, end - rate // 100) : end] ** 2)
                            ),
                            end,
                        )
                    )
                _energy, count = min(quiet)
                samples = samples[:count]
            rms = float(np.sqrt(np.mean(samples**2))) if len(samples) else 0
            text = ""
            if rms > 0.0003:
                stream = recognizer.create_stream()
                stream.accept_waveform(rate, samples)
                recognizer.decode_stream(stream)
                text = re.sub(r"<\|.*?\|>", "", stream.result.text).strip()
            item = {
                "index": len(segments) + 1,
                "from": args.start_seconds + cursor / rate,
                "to": args.start_seconds + (cursor + count) / rate,
                "text": text,
                "rms": rms,
                "source": "local SenseVoice ASR; not official subtitles",
            }
            ledger.write(json.dumps(item, ensure_ascii=False) + "\n")
            ledger.flush()
            segments.append(item)
            cursor += count
            progress = {
                "processed_seconds": cursor / rate,
                "total_seconds": total / rate,
                "segments": len(segments),
                "elapsed_seconds": time.perf_counter() - started,
                "complete": False,
            }
            (args.output_dir / "progress.json").write_text(
                json.dumps(progress), encoding="utf-8"
            )
            if len(segments) % 10 == 0 or cursor == total:
                print(
                    "ASR_PROGRESS",
                    round(cursor / rate, 1),
                    "/",
                    round(total / rate, 1),
                    "elapsed",
                    round(progress["elapsed_seconds"], 1),
                    flush=True,
                )
    content = [
        f"{s['index']}\n{stamp(s['from'])} --> {stamp(s['to'])}\n{s['text']}\n"
        for s in segments
        if s["text"]
    ]
    (args.output_dir / "automatic-study-draft.srt").write_text(
        "\n".join(content), encoding="utf-8"
    )
    (args.output_dir / "automatic-study-draft.txt").write_text(
        "\n\n".join(f"[{stamp(s['from'])}] {s['text']}" for s in segments if s["text"]),
        encoding="utf-8",
    )
    progress["complete"] = True
    progress.update(
        {
            "input": str(args.input.resolve()),
            "input_sha256": hashlib.sha256(args.input.read_bytes()).hexdigest(),
            "transcription": "machine-generated, not platform captions",
            "timestamps": "segmentation windows, not word-aligned; technical terms require verification",
        }
    )
    (args.output_dir / "progress.json").write_text(
        json.dumps(progress, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(
        "ASR_COMPLETE", len(segments), round(progress["elapsed_seconds"], 1), flush=True
    )


if __name__ == "__main__":
    main()
