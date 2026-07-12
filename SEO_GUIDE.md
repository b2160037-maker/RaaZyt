# RAAZ FILES — Free SEO (File 03) — what's automated & your 2-minute setup

Everything below is **free** and built into the pipeline. Most runs automatically
on every upload; a few things YouTube only allows manually (called out honestly).

---

## Runs automatically on EVERY upload (no action needed)

| SEO item | How it works |
|---|---|
| **Keyword research** | `src/seo.py` hits YouTube search autocomplete (free) → Google autocomplete → pytrends, builds a primary + secondary + long-tail keyword set, saved to `output/DATE/keywords.json`. If the network blocks it, it derives keywords from the topic so the run never breaks. |
| **Title** | Picks the title option containing the primary keyword, front-loads it, keeps it ≤ ~60 chars, ends with `| RAAZ FILES`. |
| **Description** | Primary keyword in the first line; keyword-rich body; **chapters/timestamps** (auto-built from scene timings, long videos ≥ 4 min); subscribe line; slogan **RAAZ KHULEGA**; disclaimer; 15 hashtags. |
| **Tags** | Primary keyword FIRST, then secondary + long-tail + topic combos + a big evergreen niche list, packed up to YouTube's ~500-char limit (long **and** Shorts). |
| **Captions (SRT)** | An SRT is built from the exact narration + timings and uploaded via the API (`captions().insert`). **Viewers see nothing on screen** (stays off) — but YouTube indexes it for search. Big ranking help with zero on-screen text. |
| **Playlists** | Each video is auto-added to a keyword-named playlist by type: *Unsolved Mysteries in Hindi / Real Mysterious Stories / Mind Blowing Facts Hindi*. Playlists rank in search and chain watch-time. |
| **Pinned first comment** | Auto-posts a keyword + question + `#RaazFiles RAAZ KHULEGA` comment to spark engagement. |
| **Shorts SEO** | `#Shorts` + primary keyword in title/desc, long-video link in the description, same 500-char tag packing, staggered release times. |
| **Consistency** | Fixed daily 4:30 PM slot (the algorithm's favourite signal). |

## Runs automatically once a WEEK (new workflow `seo_weekly.yml`, Mondays)

- **Competitor / gap scan** — searches your niche via the API, asks the model for 20 high-search / low-competition topics, and appends new ones to `topics.json`.
- **Analytics feedback** — pulls the last 28 days from the YouTube Analytics API and emails you a `seo_report.txt` summary (CTR, watch-time, etc.).
- You get an email; new topics flow into the daily topic bank automatically.

---

## Your one-time manual setup (≈ 2 minutes total)

1. **Channel keywords** (helps the whole channel rank) — YouTube Studio → Settings → Channel → **Keywords**, paste:
   ```
   raaz files, raaj files, unsolved mysteries hindi, mysterious facts, bermuda triangle,
   hindi mystery, true stories, mind blowing facts, hinglish facts, rahasya, duniya ke raaz
   ```
2. **Analytics scope** (for the weekly report) — the analytics read needs one extra permission. Just **re-run `get_token.py` once** (it now requests `yt-analytics.readonly`) and update the `YT_TOKEN_JSON` secret. Daily uploads work without this; only the weekly analytics email needs it.

---

## What YouTube does NOT allow via API (so these stay manual — being honest)

- **Cards & end-screen clickable elements** — there is **no public API** to set them. Your branded outro clip already gives the visual end-screen; if you want clickable subscribe/video elements, add them once in Studio (they can be copied to new videos with "Apply to…" — quick).
- **Pinning / hearting a comment** — the API can *post* the comment (done automatically) but can't pin or heart it. Pinning is a one-tap manual action if you want it.
- **Off-YouTube auto-posting** (Reddit, Pinterest, X, etc.) — each needs that platform's own API keys/OAuth, so it's **not** zero-setup. Not enabled by default. If you want, give me credentials for a specific platform (e.g. a Telegram bot token or Discord webhook are the easiest free ones) and I'll wire auto-posting of each new video link there.

---

## Files involved
`src/seo.py` (keywords, SRT, chapters, weekly pass) · `src/metadata.py` (keyword-loaded title/desc/tags) · `src/upload.py` (`upload_caption`) · `src/run_all.py` (wires it all) · `.github/workflows/seo_weekly.yml` · `get_token.py` (analytics scope) · `requirements.txt` (pytrends).
