#!/usr/bin/env python3
"""Download the source video once, then cut a single clip with ffmpeg.

Usage:
    python scripts/cut_clip.py <youtube_url_or_id> <start> <end> <slug> [--outdir output]

    start / end accept SS, MM:SS, or H:MM:SS.
    <slug> is a short filename stem, e.g. "cosby-prison-2026".

The full source is cached at <outdir>/<video_id>/source.mp4 and reused for later clips.
Prints the output clip path on success:  <outdir>/<video_id>/clips/<slug>.mp4
"""
import argparse
import os
import re
import subprocess
import sys


def to_seconds(t):
    t = str(t).strip()
    if re.fullmatch(r"\d+(\.\d+)?", t):
        return float(t)
    parts = [float(p) for p in t.split(":")]
    while len(parts) < 3:
        parts.insert(0, 0.0)
    h, m, s = parts
    return h * 3600 + m * 60 + s


def video_id(s):
    if "v=" in s:
        return s.split("v=")[-1].split("&")[0]
    return s.rstrip("/").split("/")[-1].split("?")[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("start")
    ap.add_argument("end")
    ap.add_argument("slug")
    ap.add_argument("--outdir", default="output")
    args = ap.parse_args()

    vid = video_id(args.video)
    url = args.video if args.video.startswith("http") else f"https://www.youtube.com/watch?v={vid}"
    d = os.path.join(args.outdir, vid)
    os.makedirs(os.path.join(d, "clips"), exist_ok=True)
    source = os.path.join(d, "source.mp4")

    if not os.path.exists(source):
        r = subprocess.run([
            "yt-dlp",
            "-f", "bv*[height<=720]+ba/b[height<=720]/best",
            "--merge-output-format", "mp4",
            "-o", source, url,
        ])
        if r.returncode != 0 or not os.path.exists(source):
            sys.stderr.write("DOWNLOAD_FAILED\n")
            sys.exit(1)

    start = to_seconds(args.start)
    dur = max(0.1, to_seconds(args.end) - start)
    out = os.path.join(d, "clips", f"{args.slug}.mp4")

    # -ss before -i with re-encode = fast seek + frame-accurate cut.
    r = subprocess.run([
        "ffmpeg", "-y",
        "-ss", str(start), "-i", source, "-t", str(dur),
        "-c:v", "libx264", "-preset", "veryfast",
        "-c:a", "aac", "-movflags", "+faststart",
        out,
    ])
    if r.returncode != 0 or not os.path.exists(out):
        sys.stderr.write("CUT_FAILED\n")
        sys.exit(1)
    print(out)


if __name__ == "__main__":
    main()
