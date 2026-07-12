#!/usr/bin/env python3
"""Sort Predictions and Prophecies — pipeline.

Given a YouTube video, this pipeline:

  1. FETCH      pull the transcript (youtube_transcript_api)
  2. EXTRACT    ask an LLM to pull out every forward-looking statement
  3. SORT       classify each one as a PREDICTION (the speaker's own forecast)
                or a PROPHECY (attributed to an external oracle / seer / scripture)
  4. REPORT     write results.json + a human-readable report.md

The EXTRACT/SORT step uses the Anthropic API when ANTHROPIC_API_KEY is set.
Without a key the pipeline still fetches and saves the transcript, and prints
the extraction prompt so the classification can be run by hand / in another
context.

Usage:
    python pipeline.py <youtube_url_or_id> [--out output]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

# --- classification schema -------------------------------------------------

CATEGORIES = {
    "prediction": "The speaker's own forecast — reasoned, intuitive, or 'psychic' "
                  "but presented as the speaker's own claim ('I predict', 'I feel', "
                  "'he is going to').",
    "prophecy":   "A forward-looking claim attributed to an EXTERNAL source: a named "
                  "seer (Nostradamus, Baba Vanga), an oracle, scripture, or tradition. "
                  "The speaker is relaying, not authoring, the claim.",
}

EXTRACTION_PROMPT = """You are analysing a transcript in which a speaker makes many \
forward-looking statements. Your job is to extract every distinct forward-looking \
statement and SORT each into exactly one of two buckets:

- "prediction": the speaker's OWN forecast (reasoned, intuitive, or psychic). \
Cues: "I predict", "I feel", "my sense is", "he's going to", "we're going to see".
- "prophecy": a forward-looking claim the speaker ATTRIBUTES TO AN EXTERNAL SOURCE \
— a named seer (Nostradamus, Baba Vanga), an oracle, scripture, or tradition. \
The speaker is relaying someone/something else's claim.

For each statement return an object:
  timestamp   : "MM:SS" of where it starts (from the [MM:SS] tags)
  category    : "prediction" | "prophecy"
  source      : who the claim is attributed to ("speaker" for predictions, else the seer/oracle)
  subject     : short topic tag (e.g. "Trump impeachment", "China", "2020 election")
  statement   : one-sentence paraphrase of the claim
  timeframe   : any date/window mentioned, else "unspecified"
  testable    : true if it is concrete enough to later score true/false, else false

Return ONLY a JSON object: {"items": [ ... ]}. No prose.

TRANSCRIPT:
"""


# --- step 1: fetch ---------------------------------------------------------

def extract_video_id(url_or_id: str) -> str:
    m = re.search(r"(?:v=|youtu\.be/|/shorts/|/embed/)([A-Za-z0-9_-]{11})", url_or_id)
    if m:
        return m.group(1)
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", url_or_id):
        return url_or_id
    raise ValueError(f"Could not parse a YouTube video id from: {url_or_id!r}")


def fetch_transcript(video_id: str) -> list[dict]:
    from youtube_transcript_api import YouTubeTranscriptApi
    api = YouTubeTranscriptApi()
    return api.fetch(video_id).to_raw_data()


def ts(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 60:02d}:{s % 60:02d}"


def timestamped_text(segments: list[dict], group_secs: int = 12) -> str:
    lines, buf, start = [], [], None
    for x in segments:
        if start is None:
            start = x["start"]
        buf.append(x["text"].strip())
        if x["start"] - start >= group_secs:
            lines.append(f"[{ts(start)}] " + " ".join(buf))
            buf, start = [], None
    if buf:
        lines.append(f"[{ts(start)}] " + " ".join(buf))
    return "\n".join(lines)


# --- step 2+3: extract & sort (LLM) ---------------------------------------

def classify_with_llm(transcript_text: str) -> dict:
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-opus-4-8",
        max_tokens=8000,
        messages=[{"role": "user", "content": EXTRACTION_PROMPT + transcript_text}],
    )
    text = msg.content[0].text.strip()
    text = re.sub(r"^```(?:json)?|```$", "", text, flags=re.MULTILINE).strip()
    return json.loads(text)


# --- step 4: report --------------------------------------------------------

def build_report(video_id: str, result: dict) -> str:
    items = result.get("items", [])
    preds = [i for i in items if i.get("category") == "prediction"]
    props = [i for i in items if i.get("category") == "prophecy"]
    out = [
        f"# Sorted Predictions & Prophecies — `{video_id}`",
        "",
        f"https://www.youtube.com/watch?v={video_id}",
        "",
        f"**{len(preds)} predictions** (speaker's own) · "
        f"**{len(props)} prophecies** (attributed to external oracles/seers)",
        "",
    ]

    badge = {"hit": "✅ hit", "miss": "❌ miss", "partial": "🟡 partial",
             "pending": "⏳ pending", "unverifiable": "❔ n/a"}

    def table(rows):
        out.append("| # | Time | Subject | Statement | Timeframe | Outcome (as scored) |")
        out.append("|---|------|---------|-----------|-----------|---------------------|")
        for n, i in enumerate(rows, 1):
            oc = badge.get(i.get("outcome_status", ""), "")
            note = i.get("outcome_note", "")
            cell = f"{oc}{' — ' + note if note else ''}".replace("|", "/")
            out.append(
                f"| {n} | {i.get('timestamp','')} | {i.get('subject','')} | "
                f"{i.get('statement','').replace('|','/')} | "
                f"{i.get('timeframe','')} | {cell} |"
            )
        out.append("")

    out.append("## Predictions (the speaker's own forecasts)\n")
    table(preds)
    out.append("## Prophecies (attributed to Nostradamus, Baba Vanga, the Indian Oracles, …)\n")
    for n, i in enumerate(props, 1):
        oc = badge.get(i.get("outcome_status", ""), "")
        out.append(f"{n}. **[{i.get('timestamp','')}] {i.get('source','')}** — "
                   f"{i.get('statement','')} _(subject: {i.get('subject','')})_ {oc}")
    out.append("")
    return "\n".join(out)


# --- driver ----------------------------------------------------------------

def main() -> int:
    ap = argparse.ArgumentParser(description="Sort predictions and prophecies from a YouTube video.")
    ap.add_argument("video", help="YouTube URL or 11-char video id")
    ap.add_argument("--out", default="output", help="output directory root")
    args = ap.parse_args()

    video_id = extract_video_id(args.video)
    out_dir = Path(args.out) / video_id
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[1/4] fetch      transcript for {video_id}")
    segments = fetch_transcript(video_id)
    (out_dir / "transcript.json").write_text(json.dumps(segments, indent=2))
    text = timestamped_text(segments)
    (out_dir / "transcript.txt").write_text(text + "\n")
    print(f"       {len(segments)} segments, {sum(len(s['text'].split()) for s in segments)} words")

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[2/4] extract    SKIPPED — ANTHROPIC_API_KEY not set.")
        print("       Transcript saved. Run the extraction prompt in an LLM context to finish sorting.")
        (out_dir / "extraction_prompt.txt").write_text(EXTRACTION_PROMPT + text)
        print(f"       Prompt written to {out_dir / 'extraction_prompt.txt'}")
        return 0

    print("[2/4] extract    forward-looking statements via Claude")
    print("[3/4] sort       into predictions vs prophecies")
    result = classify_with_llm(text)
    (out_dir / "results.json").write_text(json.dumps(result, indent=2))

    print("[4/4] report")
    (out_dir / "report.md").write_text(build_report(video_id, result))
    n = len(result.get("items", []))
    print(f"       {n} statements sorted → {out_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
