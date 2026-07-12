# Sort Predictions and Prophecies

This repo automates one job: **take a YouTube video of psychic predictions/prophecies,
extract every concrete falsifiable prediction, clip it, and file it in Airtable + Google
Drive** for review.

## When the user pastes a YouTube URL

If the user gives a YouTube URL and asks to analyze/sort/run the pipeline (or just pastes
a URL in this repo's context), **use the `prophecy-pipeline` skill** in
`.claude/skills/prophecy-pipeline/SKILL.md` and follow it end to end. That skill is the
source of truth and contains all the concrete IDs, criteria, and helper code.

The skill is **self-contained** — it writes its own helper script to
`/tmp/prophecy-pipeline` and needs nothing but `yt-dlp` + `ffmpeg`. The same skill is also
installed as an account-level claude.ai skill, so it works in any Claude Code session, not
only this repo.

Short version of what the skill does:
1. Setup: install `yt-dlp`/`ffmpeg`, write the helper (once per session).
2. Pull the timestamped transcript (**no API key**). If there's no English transcript,
   stop and say so — do not use Whisper.
3. Extract only **concrete, falsifiable, dated** predictions (high bar; skip vague ones).
4. Cut a clip per prediction (yt-dlp download once + ffmpeg).
5. Upload each clip to the Google Drive folder via the Google Drive MCP tool.
6. Create one Airtable record per prediction in the "Clips" table via the Airtable MCP tool.
7. Report back a table of what was filed.

## Key facts
- **No YouTube API key** is involved — yt-dlp scrapes anonymously, decoupled from the
  user's channel/Google account.
- **Network:** the session must reach `youtube.com` / `googlevideo.com` / `ytimg.com`.
  If yt-dlp gets a proxy 403/policy denial, the environment's network policy is blocking
  YouTube; tell the user to allow those domains and stop.
- **Airtable base** `appqabrvANN8bXH9E` → table `tblFh1XHCxSoYyhOR` ("Clips").
- **Google Drive folder** `1oleB7GOgT4oYhiKfzbGpt8r64-7b111X` ("Prophecies and Predictions").
- Analysis (which predictions qualify, categories, ratings) is done by Claude in-session,
  not by a script. The helper only handles the mechanical transcript/clip I/O.
