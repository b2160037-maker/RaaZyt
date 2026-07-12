# Owner controls — book your own topic & thumbnail for any date

You can override the automation whenever you want. If you don't, everything stays
100% automatic (SEO-report topics + auto thumbnail).

## 1. Book a topic for a specific date

Edit **`owner_requests.json`** (in the repo root) and add an entry under `requests`:

```json
{
  "requests": [
    { "date": "2026-07-08", "topic": "Kohinoor Diamond Curse", "type": "true_story" },
    { "date": "2026-07-09", "topic": "Rani of Jhansi ka Raaz" }
  ]
}
```

- `date` — the day (YYYY-MM-DD, IST) you want this topic to go out.
- `topic` — your idea, in plain words.
- `type` — optional: `unsolved_mystery` | `true_story` | `mind_blowing_fact` (default `unsolved_mystery`).

Commit/save the file. On that date the **6 AM job uses YOUR topic** instead of the
auto pick. If you booked nothing for a date, it **auto-chooses from the weekly SEO
report** (newest first), then the seed bank.

Priority order the automation follows:
**Your booked topic (for that date) → newest SEO-report topic → older unused topics → seed list.**

Notes:
- If a topic you booked was already turned into a video before, it's skipped (never repeats).
- Works with automatic runs AND manual "Run workflow" clicks — both read the latest file.

## 2. Give your own thumbnail for that day

Drop a **1280×720** image into the `thumbnails/` folder (or your Google Drive folder),
named either:

- `2026-07-08.png`  ← by **date** (easiest — matches the day), or
- `kohinoor_diamond_curse.png`  ← by **slug** (your topic in lowercase, spaces → `_`).

At 4:30 PM the automation uses your image. If you drop nothing, it auto-generates a
dramatic thumbnail. (`.png`, `.jpg`, `.jpeg`, `.webp` all accepted.)

That's it — book a topic, drop a thumbnail, or do neither and let it run itself.
