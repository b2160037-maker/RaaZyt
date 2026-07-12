"""sample_voices.py -- hear free Edge-TTS Hinglish voices, then pick your favourite.

Run locally (needs internet + edge-tts):
    pip install edge-tts
    python sample_voices.py

It writes short MP3 samples into a `voice_samples/` folder -- open them, listen,
and set your favourite as the channel voice by either:
  - editing config.py  ->  TTS_VOICE = "<voice name>"
  - OR adding a GitHub secret  TTS_VOICE = <voice name>

You can also tweak speed/pitch the same way with TTS_RATE / TTS_PITCH
(e.g. TTS_RATE=+24%, TTS_PITCH=-2Hz).
"""
import asyncio
from pathlib import Path

import edge_tts

# The line each voice will read (dramatic Hinglish, like a real script).
SAMPLE = ("Bermuda Triangle... pachhattar saal me hazaar se zyada log yahin gayab "
          "hue, aur ek bhi laash aaj tak nahi mili. Aaj main aapko wo sach bataungi "
          "jo aaj tak kisi ne nahi bataya. End tak rukna... kyunki RAAZ KHULEGA.")

# Candidate free voices worth trying for Hinglish.
VOICES = [
    "hi-IN-SwaraNeural",              # female, Hindi (current default)
    "hi-IN-MadhurNeural",             # male, Hindi
    "en-IN-NeerjaNeural",             # female, English-India: energetic, clear
    "en-IN-NeerjaExpressiveNeural",   # female, expressive (if available)
    "en-IN-PrabhatNeural",            # male, English-India: confident
]

RATE = "+20%"     # match the channel setting; change to taste
PITCH = "+0Hz"
VOLUME = "+0%"

OUT = Path(__file__).parent / "voice_samples"
OUT.mkdir(exist_ok=True)


async def one(voice: str):
    dst = OUT / f"{voice}.mp3"
    try:
        c = edge_tts.Communicate(SAMPLE, voice, rate=RATE, pitch=PITCH, volume=VOLUME)
        await c.save(str(dst))
        print(f"  OK  {dst}")
    except Exception as e:  # noqa: BLE001
        print(f"  SKIP {voice} ({e})")


async def main():
    print(f"Generating {len(VOICES)} samples at rate={RATE}, pitch={PITCH} ...")
    for v in VOICES:
        await one(v)
    print(f"\nDone. Open the '{OUT.name}' folder, listen, and set TTS_VOICE to your pick.")


if __name__ == "__main__":
    asyncio.run(main())
