# GitHub par deploy karo — RAAZ FILES (account: 4410amankumar-maker)

Ab ye channel poori tarah GitHub Actions par chalega — **tumhare laptop ki zaroorat nahi**.
API keys files se hata di gayi hain; tum unhe GitHub **Secrets** me daaloge (neeche list hai).

---

## 0. Pehle: laptop se auto-running band karo
Agar tumne pehle Windows tasks lagaye the, to unhe hatao (warna laptop bhi chalayega):
```powershell
powershell -ExecutionPolicy Bypass -File .\run\uninstall_tasks.ps1
```
(Agar lagaye hi nahi the to skip karo.)

---

## 1. Naya repo banao
1. github.com par **4410amankumar-maker** id se login karo.
2. Top-right **"+" → New repository**.
3. Naam: `raaz-files` → **Private** → **Create repository**.

## 2. Poora folder upload karo
**Sabse aasan (GitHub Desktop):**
1. GitHub Desktop install karo (desktop.github.com), 4410amankumar-maker se login.
2. File → Add local repository → ye folder chuno → "create a repository" → Publish.

**Ya git commands (agar git aata ho):**
```bash
cd "F:\extraas\claude projects\auto yt raaz"
git init
git add .
git commit -m "RAAZ FILES automation"
git branch -M main
git remote add origin https://github.com/4410amankumar-maker/raaz-files.git
git push -u origin main
```
> `.gitignore` secrets ko upload hone se rokta hai. Music/brand/outro/host clips upload honge (zaroori hain).

## 3. Secrets daalo  (Settings → Secrets and variables → Actions → New repository secret)
Har ek alag secret banao (naam bilkul same rakho):

| Secret | Value |
|---|---|
| `GEMINI_API_KEY` | tumhari Gemini key |
| `GROQ_API_KEY` | Groq key |
| `OPENROUTER_API_KEY` | OpenRouter key |
| `HF_TOKEN` | HuggingFace token |
| `PEXELS_API_KEY` | Pexels key |
| `PIXABAY_API_KEY` | Pixabay key |
| `STABLEHORDE_KEY` | Stable Horde key |
| `GMAIL_USER` | tumhara gmail |
| `GMAIL_APP_PASSWORD` | Gmail App Password (bina spaces) |
| `OWNER_EMAIL` | tumhara gmail |
| `YT_CLIENT_SECRET_JSON` | poori `client_secret.json` ki JSON (ek line) |
| `YT_TOKEN_JSON` | poori `token.json` ki JSON (ek line) |

**Optional (chaaho to):** `CHANNEL_NAME`, `TTS_VOICE` (default hi-IN-SwaraNeural), `TTS_RATE` (+20%), `YT_PRIVACY` (public).

> **YT_CLIENT_SECRET_JSON / YT_TOKEN_JSON** = tumhari purani JSON files ka poora content.
> Agar wo tumhare paas nahi hai, to apne PC par ek baar `python get_token.py` chalakar
> nayi `token.json` bana lo, phir dono files ka content in 2 secrets me paste karo.
> ⚠️ Jo keys pehle chat me di thi wo expose ho chuki — nayi banakar daalna behtar hai.

## 4. Actions on karo + test
1. Repo → **Actions** tab → "I understand..." → enable.
2. **morning-topic** → Run workflow (manual) → check topic email aata hai.
3. **publish-video** → Run workflow (manual) → video ban ke upload hoti hai (~15-25 min).
   - Fail ho to run ke logs kholo; secrets sahi hone chahiye.

## 5. Ho gaya — ab automatic
- **6:13 AM** → topic
- **12:00 PM** → long video + 3 shorts upload
- **Somwar** → SEO
- Laptop ki zaroorat nahi; sab GitHub ke free servers par.

---

## Zaroori baatein
- **Actions minutes:** private repo = 2000 min/month free. Ek din ka run us se kam hai.
  Agar kabhi minutes khatam ho to repo ko **Public** kar do (Public = unlimited free).
- **Owner topic / thumbnail** pehle jaisa kaam karega: `owner_requests.json` edit karo +
  `thumbnails/` me `<date>.png` daalo (dono committed honge → Actions padh lega).
- **Kal wala topic** ("Bharat ki Sabse Badi Bank Robbery", 2026-07-10) + uska thumbnail
  already set hai — GitHub par push karte hi wo bhi chala jayega.
