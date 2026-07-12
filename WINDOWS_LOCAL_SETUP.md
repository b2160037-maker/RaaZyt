# Windows par LOCAL automation (GitHub ke bina) — RAAZ FILES

GitHub account flag ho gaya? Koi baat nahi. Yahi project ab tumhare **Windows PC par
PowerShell + Task Scheduler** se automatic chalega — bilkul waisa ka waisa. Kuch delete
ya miss nahi hoga. (GitHub wali files bhi folder me rahengi, bas ab use nahi hongi.)

**Bada fayda:** local Task Scheduler **exact time** par chalta hai — GitHub wali "late run"
problem hi khatam.

> ⚠️ Zaroori: PC us time ON hona chahiye jab task chalna hai (12 PM publish ke waqt).
> Agar PC OFF tha, to task on karte hi apne aap chal jayega (`-StartWhenAvailable`).

---

## Ek-baar ka setup (10–15 min)

### 1. Python install karo
https://www.python.org/downloads/ → Python 3.11+ → install karte waqt **"Add Python to PATH"** tick karna.

### 2. FFmpeg install karo (video ke liye zaroori)
PowerShell kholo aur:
```powershell
winget install --id=Gyan.FFmpeg -e
```
Phir PowerShell **band karke dobara kholo** (PATH refresh ho jaye).

### 3. Project setup chalao
Is folder me PowerShell kholo (folder me Shift+Right-click → "Open PowerShell window here"), phir:
```powershell
powershell -ExecutionPolicy Bypass -File .\run\setup.ps1
```
Ye `.venv` banayega, saari Python libraries install karega, `.env` bana dega.

### 4. Apni keys bharo
- Folder me bani `.env` file ko Notepad me kholo aur apni keys paste karo
  (GEMINI_API_KEY, PEXELS_API_KEY, GMAIL_* waghairah). `.env.example` me sab likha hai.
- **YouTube:** apni `client_secret.json` aur `token.json` files isi folder me rakho.
  (`token.json` banane ke liye ek baar `python get_token.py` chalao — ye pehle jaisa hi hai.)
  In do files ke hone par `.env` me YT wali 2 lines khaali chhod sakte ho — code khud file se padh lega.

### 5. Automatic tasks laga do
PowerShell ko **"Run as Administrator"** se kholo, phir:
```powershell
powershell -ExecutionPolicy Bypass -File .\run\install_tasks.ps1
```
Ye 3 tasks laga dega:
| Task | Time (tumhare PC ka local time) | Kaam |
|---|---|---|
| RaazFiles-Morning | roz **6:00 AM** | din ka topic chunna |
| RaazFiles-Publish | roz **12:00 PM** | long video + 3 Shorts banakar upload |
| RaazFiles-Weekly | **Somwar 10:00 AM** | SEO report + naye topics |

Bas! Ab ye roz apne aap chalega.

---

## Test karo (bina intezaar kiye)
```powershell
# aaj ka topic abhi chun lo:
powershell -ExecutionPolicy Bypass -File .\run\morning.ps1
# poori video banakar upload karo (abhi):
powershell -ExecutionPolicy Bypass -File .\run\publish.ps1
```
Logs yahan milenge: `run\logs\` (har din ki alag file).

---

## Time badalna ho to
`run\install_tasks.ps1` me `-At 12:00PM` waali line badal do (jaise `-At 1:00PM`), phir
dobara chalao (Administrator PowerShell). Ya seedhe Windows **Task Scheduler** app me
task ka time edit kar do.

## Band/hataana ho to
```powershell
powershell -ExecutionPolicy Bypass -File .\run\uninstall_tasks.ps1
```

---

## Kuch delete/miss nahi hoga — kyun?
- Har run seedhe isi folder ki files update karta hai (`state.json`, `used_topics.json`,
  `topics.json`, `output\`). Koi git/commit nahi — sab tumhare PC par safe rehta hai.
- Purane GitHub workflows (`.github\`) folder me padi rahengi (delete nahi ki) — bas ab
  inki zaroorat nahi.
- Banayi hui videos `output\<date>\` me milengi (backup ke liye rehti hain; jab chaaho
  khud delete kar sakte ho — automation kuch nahi hataata).

## Owner controls waise ke waise
- Apna topic book karna: `owner_requests.json` edit karo (dekho `OWNER_CONTROLS.md`).
- Apna thumbnail: `thumbnails\` folder me `<date>.png` ya `<slug>.png` daal do.
- Sab pehle jaisa — sirf chalane ki jagah GitHub se badalkar tumhara PC ho gaya.
