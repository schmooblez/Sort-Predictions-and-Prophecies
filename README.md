# Sort Predictions and Prophecies

Automated pipeline for analyzing YouTube videos of psychic predictions / prophecies.
Give it a YouTube URL and it extracts every **concrete, falsifiable, dated** prediction,
cuts a clip for each, stores the clips in Google Drive, and files a structured record per
prediction in Airtable — ready to sort, review, and choose which to feature, highlight,
or respond to.

## How to run it

In a Claude Code session pointed at this repo (with YouTube network access enabled), just
paste a YouTube URL and ask to run the prophecy pipeline — for example:

> run the prophecy pipeline on https://www.youtube.com/watch?v=VIDEO_ID

Claude follows the **`prophecy-pipeline`** skill (`.claude/skills/prophecy-pipeline/SKILL.md`),
which is the source of truth for the whole workflow and holds every concrete detail
(Airtable base/field IDs, the Drive folder ID, extraction criteria, category taxonomy,
and the specificity-rating rubric).

## What happens

1. **Transcript** — `scripts/fetch_transcript.py` pulls a timestamped transcript with
   `yt-dlp`. No API key; if a video has no English captions, it's skipped.
2. **Analysis** — Claude reads the transcript and extracts only concrete, falsifiable,
   dated predictions (vague or undated statements are excluded).
3. **Clips** — `scripts/cut_clip.py` downloads the video once and cuts each clip with ffmpeg.
4. **Storage** — clips upload to the Google Drive folder "Prophecies and Predictions".
5. **Database** — one Airtable record per prediction in the "Clips" table, with summary,
   dates, categories, location, specificity rating, links, and review status.

## Setup

```bash
pip install -r requirements.txt
apt-get update && apt-get install -y ffmpeg    # if ffmpeg is not already present
```

Requires: a session allowed to reach `youtube.com` / `googlevideo.com` / `ytimg.com`, and
the Airtable + Google Drive connectors enabled.

## Notes

- **No YouTube API key** is used — `yt-dlp` works anonymously and is fully decoupled from
  any channel's API key or Google account.
- Downloading third-party video crosses YouTube's Terms of Service; the short-clip,
  commentary/criticism use is a fair-use posture. Use accordingly.
- The scripts only handle mechanical transcript/clip I/O; the judgment (which predictions
  qualify, their categories and ratings) is done by Claude per the skill.
