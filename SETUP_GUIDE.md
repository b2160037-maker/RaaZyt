# RAAZ FILES — Complete Setup & Deployment Guide

This is your **step-by-step, do-this-then-that** guide to take the project from these
files to a channel that publishes 1 long video + 3 Shorts every day at 4:30 PM IST —
**fully automatic, 100% free tools.**

Follow the steps in order. Total one-time setup: ~45–60 minutes. After that, it runs itself.

---

## 0. What you're deploying

Two scheduled cloud jobs on **GitHub Actions** (free):
- **06:00 AM IST** — picks the day's topic, emails you, writes `TODAY_TOPIC.txt` (so you can optionally make a thumbnail).
- **04:30 PM IST** — writes script → voice → visuals → edits the long video → builds 3 Shorts → thumbnail → uploads all to YouTube → emails you the links.

Every stage has a **free primary + free backups**, so one service being down never kills the run.

---

## 1. Create the accounts & API keys (all free)

Make these free accounts and grab each key. Keep them in a notepad for Step 3.

| # | Service | Sign-up link | What you copy |
|---|---|---|---|
| 1 | Google AI Studio (Gemini) | https://aistudio.google.com/app/apikey | `GEMINI_API_KEY` |
| 2 | Groq (script backup) | https://console.groq.com/keys | `GROQ_API_KEY` |
| 3 | OpenRouter (script backup) | https://openrouter.ai/keys | `OPENROUTER_API_KEY` |
| 4 | Hugging Face (image/script backup) | https://huggingface.co/settings/tokens | `HF_TOKEN` |
| 5 | Pexels (stock media) | https://www.pexels.com/api/ | `PEXELS_API_KEY` |
| 6 | Pixabay (stock backup) | https://pixabay.com/api/docs/ | `PIXABAY_API_KEY` |
| 7 | Stable Horde (AI image backup) | https://aihorde.net/ (anon `0000000000` works) | `STABLEHORDE_KEY` |

You only strictly need **Gemini + Pexels + YouTube** to start; the rest are backups that make it bulletproof. Add them all when you can.

---

## 2. Create the GitHub repository

1. Go to https://github.com/new → name it `raaz-files` → **Private** is fine → Create.
2. Upload **all files in this folder** to the repo (drag-and-drop in the GitHub web UI, or use Git):
   ```bash
   cd "path/to/this/folder"
   git init
   git add .
   git commit -m "RAAZ FILES automation"
   git branch -M main
   git remote add origin https://github.com/<your-username>/raaz-files.git
   git push -u origin main
   ```
   > `.gitignore` already blocks secrets/tokens from being committed. Never commit `token.json` or `client_secret.json`.

---

## 3. Add the Secrets (this is where your keys live safely)

In your repo: **Settings → Secrets and variables → Actions → New repository secret.**
Add each one (name on the left, value = the key you copied):

**Required to start**
- `GEMINI_API_KEY`
- `PEXELS_API_KEY`
- `YT_CLIENT_SECRET_JSON`  *(from Step 5)*
- `YT_TOKEN_JSON`  *(from Step 5)*
- `GMAIL_USER`  — your Gmail address
- `GMAIL_APP_PASSWORD`  *(from Step 4)*
- `OWNER_EMAIL`  — where you want the daily emails (can be the same Gmail)

**Backups (add when you can — highly recommended)**
- `GROQ_API_KEY`, `OPENROUTER_API_KEY`, `HF_TOKEN`, `PIXABAY_API_KEY`, `STABLEHORDE_KEY`

**Optional (Google Drive thumbnail folder, Step 6)**
- `RCLONE_CONF`, `RCLONE_REMOTE`

**Optional overrides**
- `CHANNEL_NAME` (default `RAAZ FILES`), `TTS_VOICE` (default `hi-IN-MadhurNeural`; female = `hi-IN-SwaraNeural`), `YT_PRIVACY` (`public`/`private`/`unlisted`).

---

## 4. Gmail App Password (for the daily emails)

1. Turn on 2-Step Verification: https://myaccount.google.com/security
2. Create an App Password: https://myaccount.google.com/apppasswords → app "Mail" → copy the 16-char password.
3. Put your Gmail in secret `GMAIL_USER` and the app password in `GMAIL_APP_PASSWORD`.

---

## 5. YouTube upload authorization (one time, ~10 min)

1. Go to https://console.cloud.google.com/ → create a project (e.g. "raaz-files").
2. **APIs & Services → Library** → search **YouTube Data API v3** → **Enable**.
3. **APIs & Services → OAuth consent screen** → External → fill required fields → add your own Google account as a **Test user**.
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID** → Application type **Desktop app** → Create → **Download JSON** → rename it `client_secret.json` and put it next to `get_token.py` in this folder.
5. On your own computer, run:
   ```bash
   pip install google-auth-oauthlib google-api-python-client
   python get_token.py
   ```
   A browser opens → sign in with the Google account that owns your YouTube channel → approve. It writes `token.json`.
6. Paste the **contents** of the two files into GitHub Secrets:
   - `client_secret.json` → secret `YT_CLIENT_SECRET_JSON`
   - `token.json` → secret `YT_TOKEN_JSON`

From now on the cloud refreshes the token automatically — you never log in again.

> ⚠️ Never commit `client_secret.json` or `token.json` — `.gitignore` already blocks them.

---

## 6. (Optional) Google Drive thumbnail folder — drop thumbnails from your phone

If you want to drop custom thumbnails from your phone instead of the GitHub UI:
1. Install rclone locally: https://rclone.org/downloads/
2. `rclone config` → create a **drive** remote named `gdrive` pointing at a folder (e.g. `raaz-thumbnails`).
3. Copy your `~/.config/rclone/rclone.conf` contents into secret `RCLONE_CONF`.
4. Set secret `RCLONE_REMOTE` to `gdrive:raaz-thumbnails`.

**Don't want this?** Skip it. The **backup path already works**: the bot writes `TODAY_TOPIC.txt` into the repo `thumbnails/` folder, and you can drop a `<slug>.png` there from the GitHub web UI. And if you drop nothing, it auto-generates one.

---

## 7. Create the brand assets (create ONCE)

You said you'll supply these. Put them in `assets/brand/` (see `assets/brand/README.md`), **or** auto-generate them free:
```bash
pip install -r requirements.txt
python make_brand_assets.py
```
This makes `signature_sting.wav`, `logo_sting.mp4`, `avatar.png`, `banner.png` — and **skips any file you already placed** so your own art is never overwritten.
Also drop the free **Anton**/**Bebas Neue** fonts into `assets/brand/fonts/` and a couple of royalty-free tracks into `assets/music/` (see those folders' READMEs).

Commit the assets you want version-controlled (note: `.gitignore` skips the heavy media by default; remove those lines if you'd rather commit them).

---

## 8. TEST before trusting the schedule

In your repo → **Actions** tab:
1. Run **morning-topic** → **Run workflow** (manual). Check: you get the topic email + `TODAY_TOPIC.txt` is committed.
2. Run **publish-video** → **Run workflow** (manual). Watch the logs. On success you get the "✅ Done" email with the video + 3 short links, and `output/<date>/` is saved as an Actions **artifact**.

If a run fails, you get a "❌ failed" email with the error, and **nothing broken is uploaded** (the QA gate blocks it).

---

## 9. You're live

Once the manual tests pass, the two cron schedules run every day on their own:
- `30 0 * * *` → 06:00 IST (topic)
- `0 11 * * *` → 16:30 IST (publish)

GitHub cron can start a few minutes late — that's normal.

---

## 10. Day-to-day (nothing required)

- **Do nothing** and it publishes daily.
- **Optional:** when you get the 6 AM email, make a 1280×720 thumbnail and drop it as `<slug>.png` in the Drive folder or repo `thumbnails/`.
- Watch the **Actions** tab if you ever want to see a run or re-run one.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| No email | Check `GMAIL_APP_PASSWORD` (must be an App Password, not your login) and `OWNER_EMAIL`. |
| Upload fails "creds invalid" | Re-run `get_token.py`, update `YT_TOKEN_JSON`. Make sure your account is a **Test user** on the OAuth consent screen. |
| "QA gate FAILED" | Open the run's `qa_report.txt` artifact — it lists exactly what failed. Usually a missing visual/audio; re-run. |
| Script/voice/image errors | The backups auto-kick-in; add the backup keys (Groq/HF/Pixabay) so there's always a fallback. |
| Quota hit on YouTube | 1 long + 3 shorts ≈ 6,400 units < 10,000/day free. If exceeded, it logs and retries next day; you can request a free quota bump in Cloud Console. |
| Actions out of minutes | Public repos = unlimited. Or use a backup runtime (see `02_GITHUB_DEPLOYMENT_PROMPT.md` §7: Colab / local Task Scheduler). |

---

**That's it.** Files build the videos, workflows run them free in the cloud, secrets keep your keys safe, and the QA gate guarantees nothing flawed goes public.
