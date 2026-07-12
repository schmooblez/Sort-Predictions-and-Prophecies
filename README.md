# Sort Predictions and Prophecies

Automated pipeline for analyzing YouTube videos of psychic predictions / prophecies.
Give it a YouTube URL and it extracts every **concrete, falsifiable, dated** prediction,
cuts a clip for each, stores the clips in Google Drive, and files a structured record per
prediction in Airtable — ready to sort, review, and choose which to feature, highlight,
or respond to.

## How to run it

In a Claude Code session with YouTube network access and the Airtable + Google Drive
connectors enabled, just paste a YouTube URL and ask to run the prophecy pipeline:

> run the prophecy pipeline on https://www.youtube.com/watch?v=VIDEO_ID

Claude follows the **`prophecy-pipeline`** skill (`.claude/skills/prophecy-pipeline/SKILL.md`),
which is the source of truth for the whole workflow and holds every concrete detail
(Airtable base/field IDs, the Drive folder ID, extraction criteria, category taxonomy,
the specificity-rating rubric, and the embedded helper code).

The skill is **self-contained**: it writes its own helper script to `/tmp/prophecy-pipeline`
at runtime and depends only on `yt-dlp` + `ffmpeg`. It is also installed as an
account-level claude.ai skill, so it runs in any Claude Code session — this repo is just
the versioned home for it.

## What happens

1. **Transcript** — a timestamped transcript is pulled with `yt-dlp`. No API key; if a
   video has no English captions, it's skipped.
2. **Analysis** — Claude reads the transcript and extracts only concrete, falsifiable,
   dated predictions (vague or undated statements are excluded).
3. **Clips** — the video downloads once and each clip is cut with ffmpeg.
4. **Storage** — clips upload to the Google Drive folder "Prophecies and Predictions".
5. **Database** — one Airtable record per prediction in the "Clips" table, with summary,
   dates, categories, location, specificity rating, links, and review status.

## Requirements

- A Claude Code session allowed to reach `youtube.com` / `googlevideo.com` / `ytimg.com`.
- The Airtable and Google Drive MCP connectors enabled.
- `yt-dlp` (installed automatically by the skill) and `ffmpeg` (system package).

## Notes

- **No YouTube API key** is used — `yt-dlp` works anonymously and is fully decoupled from
  any channel's API key or Google account.
- Downloading third-party video crosses YouTube's Terms of Service; the short-clip,
  commentary/criticism use is a fair-use posture. Use accordingly.
- The helper only handles mechanical transcript/clip I/O; the judgment (which predictions
  qualify, their categories and ratings) is done by Claude per the skill.
