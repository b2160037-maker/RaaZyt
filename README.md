# RAAZ FILES — Fully Automated Hinglish Mystery YouTube Channel

Zero-human-touch pipeline that publishes **1 long-form video + 3 promo Shorts every day
at 4:30 PM IST**, using **100% free tools** with a backup for every stage.

Topics: unsolved mysteries, true stories, mind-blowing facts. Hinglish voice-over,
no on-screen captions, cinematic hook → twist → payoff structure.

> **New here? Read [`SETUP_GUIDE.md`](SETUP_GUIDE.md) — it walks you through every step.**

---

## How it works

```
06:00 IST  morning.yml  → src.topic --announce   (pick topic, email you, write TODAY_TOPIC.txt)
16:30 IST  publish.yml   → src.run_all            (build everything + upload)

run_all:  topic → script → tts → visuals → edit(long) → thumbnail
        → shorts(3) → metadata → QA gate → upload long → inject URL → upload shorts → notify
```

## Reliability (free primary → free backups)

| Stage | Primary | Backups |
|---|---|---|
| Script | Gemini | Groq → OpenRouter → HuggingFace |
| Voice | Edge-TTS | gTTS → Piper |
| AI image | Pollinations | Stable Horde → HF → Craiyon |
| Stock media | Pexels | Pixabay → Wikimedia |
| Editing | MoviePy | FFmpeg |
| Thumbnail | Owner drop (Drive/repo) | Auto-gen (Pollinations→Horde) |
| Upload | YouTube Data API v3 | resumable + retry |

## Project layout

```
config.py                 all settings + keys (from env/secrets)
requirements.txt          free Python deps
topics.json               topic bank (no repeats via used_topics.json)
make_brand_assets.py      one-time free brand asset generator
get_token.py              one-time YouTube OAuth helper
src/
  utils.py fallback.py    shared helpers + provider-chain runner
  topic.py notify.py      topic selection + owner email
  script.py               LLM chain, meta-prompt, fact-check pass
  tts.py                  narration audio (Edge→gTTS→Piper), loudnorm
  visuals.py              AI images + stock, matched to narration
  edit.py                 MoviePy assembly: Ken Burns, crossfades, music duck, sting
  thumbnail.py            owner-drop scan + auto-gen + overlay
  shorts.py               3 different vertical Shorts
  metadata.py             SEO title/description/tags
  qa.py                   quality gate (blocks bad uploads)
  upload.py               YouTube resumable upload + thumbnail + pin + playlist
  run_all.py              4:30 PM orchestrator
.github/workflows/        morning.yml (6AM) · publish.yml (4:30PM)
assets/brand|music|sfx    reusable identity + audio (see each folder's README)
thumbnails/               daily TODAY_TOPIC.txt + your optional drops
output/YYYY-MM-DD/        long.mp4, short1-3.mp4, thumb.png, script.json, meta.json, qa_report.txt
```

## Local test

```bash
pip install -r requirements.txt
sudo apt-get install -y ffmpeg fonts-dejavu       # (Linux/Actions)
# set keys in a local .env (see config.py), then:
python -m src.topic --announce
python -m src.run_all
```

## Safety

- No keys in code — everything from env / GitHub Secrets. `.gitignore` blocks token files.
- Nothing uploads unless `qa.py` passes. Failures email you and upload nothing.
- Every run keeps outputs as a GitHub artifact + commits the metadata log.

Built to the spec in `01_MASTER_AUTOMATION_PROMPT.md` + `02_GITHUB_DEPLOYMENT_PROMPT.md`.
"# RaaZyt" 
