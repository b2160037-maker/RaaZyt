"""script.py — generate the Hinglish narration script via LLM chain.

Provider order (auto-fallback): Gemini -> Groq -> OpenRouter -> HuggingFace.
Produces STRICT JSON validated against the schema in File 1 Section 4,
then runs a fact-check rewrite pass.
"""
from __future__ import annotations

import random

import config as C
from .utils import get_logger, extract_json, http_get
from .fallback import try_chain

log = get_logger("script")


# ---------------------------------------------------------------------------
# Low-level single-call LLM helpers (each raises on failure)
# ---------------------------------------------------------------------------
def _gemini(prompt: str) -> str:
    if not C.GEMINI_API_KEY:
        raise RuntimeError("no GEMINI_API_KEY")
    import google.generativeai as genai
    genai.configure(api_key=C.GEMINI_API_KEY)
    model = genai.GenerativeModel(C.GEMINI_MODEL)
    resp = model.generate_content(prompt)
    return resp.text


def _groq(prompt: str) -> str:
    if not C.GROQ_API_KEY:
        raise RuntimeError("no GROQ_API_KEY")
    from groq import Groq
    client = Groq(api_key=C.GROQ_API_KEY)
    resp = client.chat.completions.create(
        model=C.GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.8,
    )
    return resp.choices[0].message.content


def _openrouter(prompt: str) -> str:
    if not C.OPENROUTER_API_KEY:
        raise RuntimeError("no OPENROUTER_API_KEY")
    import requests
    r = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {C.OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": C.OPENROUTER_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.8,
        },
        timeout=120,
    )
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _hf(prompt: str) -> str:
    if not C.HF_TOKEN:
        raise RuntimeError("no HF_TOKEN")
    import requests
    r = requests.post(
        f"https://api-inference.huggingface.co/models/{C.HF_TEXT_MODEL}",
        headers={"Authorization": f"Bearer {C.HF_TOKEN}"},
        json={"inputs": prompt, "parameters": {"max_new_tokens": 3000, "return_full_text": False}},
        timeout=120,
    )
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list) and data:
        return data[0].get("generated_text", "")
    return str(data)


def call_llm(prompt: str) -> str:
    """Text-in / text-out across the provider chain (used by topic & script)."""
    return try_chain(
        "llm",
        [
            ("gemini", lambda: _gemini(prompt)),
            ("groq", lambda: _groq(prompt)),
            ("openrouter", lambda: _openrouter(prompt)),
            ("huggingface", lambda: _hf(prompt)),
        ],
    )


# ---------------------------------------------------------------------------
# Meta-prompt (File 1 Section 4)
# ---------------------------------------------------------------------------
META_PROMPT = """Tum ek viral Hinglish YouTube storyteller ho jiska channel "{CHANNEL}" hai — unsolved mysteries, true stories aur mind-blowing facts.
Topic: {TOPIC}
Ek narration script likho SIRF Hinglish me (Hindi + English natural mix, jaise log bolte hain), spoken tone, NO stage directions inside the spoken lines.

Rules:
1. Sabse pehle ek COLD-OPEN HOOK line do (max 2 sentences) jo sabse shocking ho — isse video shuru hoga.
2. Phir promise + open loop (end tak rukne ka reason).
3. Body ko chhote beats me todo. Har 30-45 sec par ek micro-hook.
4. Ek clear [TWIST] daalo 60-70% par — "aapko laga X, par asli sach Y".
5. Ending: emotional/curiosity payoff + ek line jo agli video dekhne ko force kare.
6. Facts real aur verifiable hon. Agar koi cheez theory hai to "kaha jata hai" bolo, fact ki tarah nahi.
7. Tone: cinematic, thriller, thoda darr + thoda wonder. Simple words. Koi cringe nahi.
8. Length: approx {MINUTES} minutes of speaking (~150 Hindi-English words per minute).
9. Jis scene me host ko camera pe dikhana ho (jaise jab host seedhe darshak se baat kare, sawaal poochhe, ya personal opinion de) wahan us scene me "host": true karo. Baaki visual-driven scenes me "host": false.

Output STRICT JSON ONLY (no markdown, no commentary):
{{
  "title_options": ["...", "...", "..."],
  "cold_open": "...",
  "hook_promise": "...",
  "scenes": [
     {{"narration": "...", "visual_query": "english search/gen keywords for this scene image/clip", "mood": "tense|calm|reveal", "onscreen_seconds": 6, "host": false}}
  ],
  "twist_scene_index": 0,
  "ending": "...",
  "cta": "...",
  "description": "...",
  "tags": ["...", "15-20 tags"]
}}"""

FACTCHECK_PROMPT = """Yeh ek YouTube narration script JSON hai. Har claim check karo:
- Agar koi claim historically FALSE hai ya unverifiable hai, use "kaha jata hai" / "maana jata hai" ke andaz me rewrite karo (theory ki tarah, fact ki tarah nahi).
- Baaki sab kuch same rakho. Scene count aur structure change mat karo.
Return the SAME STRICT JSON schema, corrected. JSON ONLY.

SCRIPT:
{SCRIPT}"""


def _target_minutes(topic_type: str) -> int:
    if topic_type == "mind_blowing_fact":
        return random.randint(C.MIN_MINUTES, 6)
    if topic_type == "true_story":
        return random.randint(6, 10)
    return random.randint(8, C.MAX_MINUTES)  # unsolved_mystery -> deep dive


def _validate(data: dict) -> dict:
    required = ["cold_open", "hook_promise", "scenes", "ending", "cta"]
    for k in required:
        if k not in data:
            raise ValueError(f"script JSON missing '{k}'")
    if not isinstance(data["scenes"], list) or not data["scenes"]:
        raise ValueError("script JSON has no scenes")
    for i, sc in enumerate(data["scenes"]):
        sc.setdefault("visual_query", data.get("cold_open", "mystery")[:60])
        sc.setdefault("mood", "tense")
        sc.setdefault("onscreen_seconds", 6)
        sc.setdefault("host", False)
        if not sc.get("narration"):
            raise ValueError(f"scene {i} missing narration")
    data.setdefault("title_options", [data["scenes"][0]["narration"][:50]])
    data.setdefault("tags", ["mystery", "unsolved", "hindi", "facts", "story"])
    data.setdefault("description", data.get("hook_promise", ""))
    data.setdefault("twist_scene_index", int(len(data["scenes"]) * 0.65))
    return data


def generate(topic: str, topic_type: str = "unsolved_mystery") -> dict:
    minutes = _target_minutes(topic_type)
    prompt = META_PROMPT.format(
        CHANNEL=C.CHANNEL_NAME, TOPIC=topic, MINUTES=minutes
    )

    def _attempt() -> dict:
        raw = call_llm(prompt)
        return _validate(extract_json(raw))

    # try once; on malformed JSON, the chain / retry handles it
    try:
        data = _attempt()
    except Exception as e:  # noqa: BLE001
        log.warning("first script attempt failed (%s) — retrying once", e)
        data = _attempt()

    # fact-check pass (best-effort; never fatal)
    try:
        import json as _json
        checked = extract_json(
            call_llm(FACTCHECK_PROMPT.format(SCRIPT=_json.dumps(data, ensure_ascii=False)))
        )
        data = _validate(checked)
        log.info("fact-check pass applied")
    except Exception as e:  # noqa: BLE001
        log.warning("fact-check pass skipped (%s) — using original", e)

    log.info("script ready: %d scenes, ~%d min target", len(data["scenes"]), minutes)
    return data
