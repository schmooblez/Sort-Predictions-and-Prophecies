---
name: prophecy-pipeline
description: >-
  Analyze a YouTube video for concrete, falsifiable psychic predictions / prophecies
  and file each one into Airtable with a clip in Google Drive. Use whenever the user
  pastes a YouTube URL and wants prophecies/predictions extracted, or references the
  "prophecy pipeline". Pulls the timestamped transcript (no API key), extracts only
  dated, falsifiable predictions, cuts a clip per prediction to Google Drive, and
  creates one Airtable record per prediction in the "Clips" table.
---

# Prophecy Pipeline

Turn a single YouTube URL into sorted, clipped, filed **failed-prophecy** records.

The channels analyzed feature psychics/prophets making predictions. This pipeline
finds each **concrete, falsifiable, dated** prediction, cuts the relevant clip, stores
it in Google Drive, and files a structured row in Airtable so the user can sort,
review, and choose which to feature/highlight/respond to.

## What "run the pipeline" means

Given a YouTube URL, do all of this end to end:

1. **Fetch** the timestamped transcript + metadata (`scripts/fetch_transcript.py`).
2. **Analyze** the transcript and extract every qualifying prediction (see criteria).
3. **Clip** the relevant span of the video for each prediction (`scripts/cut_clip.py`).
4. **Upload** each clip to the Google Drive folder.
5. **File** one Airtable record per prediction in the "Clips" table.
6. **Report** back a short table of what was filed.

If the video has **no English transcript**, stop and tell the user "No transcript
available — skipping this video." (Do not attempt Whisper; that was intentionally
descoped.)

## Environment requirements

- **Network:** the session must be allowed to reach `youtube.com`, `googlevideo.com`,
  and `ytimg.com`. If yt-dlp fails with a proxy `403 CONNECT`/policy denial, the
  environment's network policy is blocking YouTube — tell the user it needs to allow
  those domains (Claude Code on the web → environment settings → network access) and stop.
- **No API key needed.** `yt-dlp` scrapes anonymously; it never touches the user's
  YouTube Data API key or Google account. Do not ask for or use a YouTube API key.
- **Tools:** `yt-dlp` (pip) and `ffmpeg` (system). Install if missing:
  `pip install -r requirements.txt` and `apt-get update && apt-get install -y ffmpeg`.

## Step 1 — Fetch transcript + metadata

```bash
pip install -q -r requirements.txt          # yt-dlp
python scripts/fetch_transcript.py "<YOUTUBE_URL>"
```

Writes to `output/<video_id>/`:
- `metadata.json` — id, title, channel, upload_date (YYYYMMDD), duration, webpage_url
- `transcript.json` — list of `{start, dur, text}` (seconds)
- `transcript.txt` — readable, each line prefixed `[H:MM:SS]`

If the script exits with `NO_TRANSCRIPT`, stop per the rule above.
Read `metadata.json` and `transcript.txt` before analyzing.

## Step 2 — Extract qualifying predictions

Read the whole transcript. Pull out **each individual instance** of a prediction that
is **concrete AND falsifiable AND dated**. Quality bar is high — most vague statements
do NOT qualify.

**INCLUDE** (examples of the bar):
- "Bill Cosby will go to prison in 2026."
- "Trump will win the 2020 election."
- "Denzel Washington will win Best Actor at the 2025 Oscars."
- "There will be a major earthquake in Tokyo before June 2027."
- A named person will die / marry / divorce / be arrested by a specific time.

**EXCLUDE** (do not file these):
- Vague/unfalsifiable: "2022 will be a good year", "there will be extreme weather."
- Undated / open-ended: "eventually this person will get divorced."
- No concrete subject or outcome.

For a location-based claim (e.g. terror attack, disaster), **only include it if a place
is named** — the more specific the better (building > city > state/region > country).
Record that place in `Location` and set `Location Specificity`.

For each qualifying prediction, determine:
- A one-line **summary** ("<who/what> will <outcome> <when>").
- The **exact quote** (verbatim from transcript).
- **Clip start/end** timestamps: start a few seconds before the setup, end when the
  claim finishes. Keep clips tight (roughly 15–90s).
- **Date made** = date stated in the video; if none, default to the video's
  `upload_date`.
- **Fulfillment date** = when it's supposed to happen, most precise available; also set
  **Fulfillment Precision** (Exact day / Month / Quarter / Year / Vague / undated).
- **Primary Category** (1+) and **Subcategory** (0+) from the taxonomy below.
- **Location** + **Location Specificity** when a place is named.
- **Specificity Rating (1–10)** — see rubric.
- Leave **Outcome** = "Pending (not yet due)" unless the fulfillment date has already
  passed and you can judge it; then set Failed / Came true / Partial.
- Leave **Review Status** = "Unreviewed".

### Specificity Rating rubric (1–10)
How specific/unlikely the prediction is — i.e. how impressive it would be if it hit.
- **1–2** = trivially likely / near-certain ("earthquakes in California this year").
- **4–6** = plausible but non-obvious, some specificity (named person, rough timeframe).
- **8–10** = extremely specific & near-impossible to know in advance (named person, exact
  date, specific cause/outcome — e.g. "Ted Cruz has a heart attack on 2028-06-12, is
  hospitalized 3 days, then dies of a medication error").

### Category taxonomy
Primary Category (multi): Economic · Natural Disaster · Political · War / Violence ·
Celebrity / Gossip · Sports · Media / Entertainment · Other.
Subcategory is a single pooled multi-select (a clip may carry tags from several
categories — that's expected). The full option list lives in the Airtable field; pick
the ones that fit and **only use option names that already exist** in the field (fetch
them with `list_tables_for_base` / `get_table_schema` if unsure). Representative options:
- Economic: Recession, Depression, Economic collapse, Stock market crash/boom, Inflation / prices, Trade / tariffs, Monetary-order shift, Crypto, Unemployment, Housing market, Bank / institution failure
- Natural Disaster: Earthquake, Hurricane, Tornado, Wildfire, Flood, Tsunami, Volcano, Blizzard / winter storm, Drought, Landslide, Pandemic / disease
- Political: Election victory/defeat, Assassination, Candidate drops out, Impeachment, Resignation, Chamber control flip, Legislation / policy, Coup, Political scandal, Court / legal ruling
- War / Violence: War outbreak, Military strike, Terrorism, Mass shooting, Murder, Kidnapping, Assassination attempt, Civil unrest / riot, Nuclear event
- Celebrity / Gossip: Award win, Marriage, Divorce, Celebrity death, Pregnancy / baby, Retirement / quitting, Arrest / prison, Breakup, Health / illness, Comeback, Affair / scandal
- Sports: Game winner, Championship / title, Final score, Player trade / signing, Injury, Record broken
- Media / Entertainment: Box office record, Film release / slate, TV / streaming, Music / album release, Franchise / sequel, Casting, Studio / company deal, Cancellation
- Other: Technology / AI, Space / UFO, Royal family, Religious event, Science / discovery, Weather (non-disaster)

If a genuinely new subcategory is needed, create it with `create_field`'s option set or
tell the user — do not silently drop a good tag.

## Step 3 — Cut a clip per prediction

The source video downloads once and is reused for all clips.

```bash
python scripts/cut_clip.py "<YOUTUBE_URL>" <start> <end> <slug>
# start/end accept SS, MM:SS, or H:MM:SS. <slug> is a short filename, e.g. cosby-prison-2026
```

Prints the path `output/<video_id>/clips/<slug>.mp4`.

## Step 4 — Upload each clip to Google Drive

Use the Google Drive MCP tool `create_file`:
- `parentId`: **`1oleB7GOgT4oYhiKfzbGpt8r64-7b111X`**  (folder "Prophecies and Predictions")
- `title`: `<video_id>__<slug>.mp4`
- `base64Content`: base64 of the clip file
- `contentMimeType`: `video/mp4`
- `disableConversionToGoogleType`: true

From the returned file `id`, the clip URL for Airtable is
`https://drive.google.com/file/d/<id>/view`.
(Very large clips can exceed upload limits — keep clips tight; if one fails, tell the user.)

## Step 5 — Create the Airtable record

Base **`appqabrvANN8bXH9E`** ("Prophecies And Psychic Predictions"),
table **`tblFh1XHCxSoYyhOR`** ("Clips"). Use `create_records_for_table` with these field IDs:

| Field ID | Field name | Value |
|---|---|---|
| `flddAd56mwhuNnMKw` | Prediction Summary (primary) | one-line summary |
| `fldhv2f4Ao615gBQD` | Predictor Name | psychic/prophet named (fallback: channel) |
| `fld8rzbTcaTJd3YBr` | Channel Name | from metadata |
| `fldDEZvmxxZOTqNCo` | Video Title | from metadata |
| `fldMzTHLorj9xQQmj` | Source URL (timestamped) | `https://www.youtube.com/watch?v=<id>&t=<startSeconds>s` |
| `fldPwPqxcRxScoShY` | Clip URL (Drive) | Drive view link from step 4 |
| `fldRjSAFnb1dV2Mrt` | Clip Start | `H:MM:SS` |
| `fld4Bwo2hcGoxspIq` | Clip End | `H:MM:SS` |
| `fldZLogQU2pxDo0RT` | Exact Quote | verbatim |
| `fldAoRiN11UZ3O5qP` | Date Prediction Made | `YYYY-MM-DD` |
| `fldZqk2kpIq9YZibN` | Fulfillment Date | `YYYY-MM-DD` (best precision available) |
| `fldGzwrb8GtxO703e` | Fulfillment Precision | one of: Exact day · Month · Quarter · Year · Vague / undated |
| `fldBDvcaZI1VeQP6J` | Outcome | Failed · Came true · Partial · Pending (not yet due) |
| `fldSvO2CYs4J1q7XD` | Primary Category | array of category names |
| `fldYRfw9ksQulvij3` | Subcategory | array of subcategory names |
| `fldf66bBFv8mFP88f` | Location | named place, or leave blank |
| `fldPwvq1ehAlTEWrH` | Location Specificity | Venue / Building · City · State / Region · Country · None given |
| `fldqxqWRpjbe80MXQ` | Specificity Rating (1-10) | integer 1–10 |
| `fldavH9NwQi0xY1pd` | Review Status | Unreviewed (default) |
| `fldsZ7U07AFAG4BR8` | Notes | anything useful |

Do **not** write `Timeframe Status` (`fld7mmGcT4GJqDCzK`) — it's an auto formula.
For select fields pass the option **name** as a plain string (arrays for the two
multi-selects). If a field ID ever fails to resolve (e.g. the base was rebuilt),
re-resolve IDs by name via `list_tables_for_base` before writing.

You can batch up to 50 records in one `create_records_for_table` call.

## Step 6 — Report

Reply with a compact table: summary · fulfillment date · category · specificity rating ·
Drive link, plus a count and any predictions you deliberately excluded as too vague.

## Constants (quick reference)
- Airtable base: `appqabrvANN8bXH9E` · table `tblFh1XHCxSoYyhOR`
- Drive folder: `1oleB7GOgT4oYhiKfzbGpt8r64-7b111X` ("Prophecies and Predictions")
