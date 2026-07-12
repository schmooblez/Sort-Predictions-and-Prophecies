#!/usr/bin/env python3
"""Fetch YouTube metadata + a timestamped transcript using yt-dlp (no API key).

Usage:
    python scripts/fetch_transcript.py <youtube_url> [--outdir output]

Writes to <outdir>/<video_id>/:
    metadata.json    - id, title, channel, upload_date (YYYYMMDD), duration, webpage_url
    transcript.json  - list of {start, dur, text} in seconds
    transcript.txt   - readable, each line prefixed [H:MM:SS]

Exit codes:
    0  success
    2  NO_TRANSCRIPT (no English captions) -> caller should skip the video
    1  other failure
"""
import argparse
import glob
import json
import os
import subprocess
import sys


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def hms(sec):
    sec = int(sec)
    h, rem = divmod(sec, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--outdir", default="output")
    args = ap.parse_args()

    # 1. Metadata (single JSON dump, no download).
    r = run(["yt-dlp", "-J", "--skip-download", args.url])
    if r.returncode != 0:
        sys.stderr.write(r.stderr or "yt-dlp metadata fetch failed\n")
        sys.exit(1)
    info = json.loads(r.stdout)
    vid = info["id"]
    d = os.path.join(args.outdir, vid)
    os.makedirs(d, exist_ok=True)

    meta = {
        "id": vid,
        "title": info.get("title"),
        "channel": info.get("channel") or info.get("uploader"),
        "uploader": info.get("uploader"),
        "upload_date": info.get("upload_date"),  # YYYYMMDD
        "duration": info.get("duration"),
        "webpage_url": info.get("webpage_url"),
        "description": info.get("description"),
    }
    with open(os.path.join(d, "metadata.json"), "w") as f:
        json.dump(meta, f, indent=2)

    # 2. Captions: prefer human/manual English subs, else auto-generated. json3 carries
    #    per-event start/duration, which is what we need for clip timestamps.
    subs = info.get("subtitles") or {}
    have_manual = any(k.startswith("en") for k in subs)
    lang_sel = "en.*,en"
    base_cmd = [
        "yt-dlp", "--skip-download", "--sub-langs", lang_sel,
        "--sub-format", "json3", "-o", os.path.join(d, "%(id)s"), args.url,
    ]
    run(base_cmd + (["--write-subs"] if have_manual else ["--write-auto-subs"]))
    files = sorted(glob.glob(os.path.join(d, f"{vid}*.json3")))
    if not files:
        # Fallback: try auto-captions explicitly.
        run(base_cmd + ["--write-auto-subs"])
        files = sorted(glob.glob(os.path.join(d, f"{vid}*.json3")))
    if not files:
        sys.stderr.write(f"NO_TRANSCRIPT: no English captions available for {vid}\n")
        sys.exit(2)

    with open(files[0]) as f:
        j3 = json.load(f)

    segments = []
    last_text = None
    for ev in j3.get("events", []):
        if "segs" not in ev:
            continue
        text = "".join(s.get("utf8", "") for s in ev["segs"]).strip()
        if not text or text == last_text:
            continue
        last_text = text
        segments.append({
            "start": round(ev.get("tStartMs", 0) / 1000.0, 2),
            "dur": round(ev.get("dDurationMs", 0) / 1000.0, 2),
            "text": text,
        })

    with open(os.path.join(d, "transcript.json"), "w") as f:
        json.dump(segments, f, indent=2)
    with open(os.path.join(d, "transcript.txt"), "w") as f:
        for s in segments:
            f.write(f"[{hms(s['start'])}] {s['text']}\n")

    print(f"OK {vid}: {len(segments)} segments | {meta['title']!r} | {meta['channel']}")
    print(f"  metadata:   {os.path.join(d, 'metadata.json')}")
    print(f"  transcript: {os.path.join(d, 'transcript.txt')}")


if __name__ == "__main__":
    main()
