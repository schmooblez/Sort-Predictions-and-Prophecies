# Sort Predictions and Prophecies

A small pipeline that takes a YouTube video, pulls the transcript, and **sorts
every forward-looking statement into two buckets**:

- **Prediction** — the speaker's *own* forecast (reasoned, intuitive, or psychic).
- **Prophecy** — a claim the speaker *attributes to an external source*: a named
  seer (Nostradamus, Baba Vanga), an oracle, scripture, or tradition.

## Pipeline stages

1. **Fetch** — transcript via `youtube_transcript_api`.
2. **Extract** — an LLM pulls out each distinct forward-looking statement.
3. **Sort** — each statement is classified as *prediction* vs *prophecy*, with a
   subject tag, timeframe, and testability flag.
4. **Report** — writes `results.json` and a human-readable `report.md`.

## Usage

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...      # step 2+3 use the Anthropic API
python pipeline.py "https://www.youtube.com/watch?v=VIDEO_ID"
```

Without `ANTHROPIC_API_KEY` the pipeline still fetches and saves the transcript
and writes `extraction_prompt.txt`, so the sort can be finished in any LLM
context. Output lands in `output/<video_id>/`.

## Example run

`output/ELPYVE3om9w/` holds a completed run on a Dec-2019 Craig Hamilton-Parker
video about Donald Trump — **17 predictions** and **6 prophecies** (Nostradamus,
Baba Vanga, ancient Tamil Oracles). See [`report.md`](output/ELPYVE3om9w/report.md).
Outcomes in that run were scored by hand against real-world events as of
2026-07-12 (the `outcome_status` / `outcome_note` fields); the base pipeline
produces the prediction/prophecy sort, and outcome-scoring is an optional
enrichment layer on top.
