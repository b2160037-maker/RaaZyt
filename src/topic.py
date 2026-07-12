"""topic.py — pick the day's topic (no repeats), announce it, save state.

Run modes:
    python -m src.topic --announce   # 6 AM job: pick + write TODAY_TOPIC.txt + email + Drive push
    python -m src.topic --show       # print today's saved topic (used by 4:30 PM job)
"""
from __future__ import annotations

import argparse
import datetime as dt
import random
import sys

import config as C
from .utils import get_logger, read_json, write_json, slugify, run, have
from . import notify

log = get_logger("topic")


def today_str() -> str:
    return dt.date.today().isoformat()


def _load_bank() -> list[dict]:
    data = read_json(C.TOPICS_FILE, {"topics": []})
    return data.get("topics", [])


def _load_used() -> list[dict]:
    data = read_json(C.USED_TOPICS_FILE, {"used": []})
    return data.get("used", [])


def _used_names(used: list[dict]) -> set[str]:
    return {u.get("slug") for u in used}


def _owner_request_for(date: str, used_slugs: set[str]) -> dict | None:
    """If the owner pre-booked a topic for THIS date (owner_requests.json), use it
    (highest priority) -- unless it was already made into a video."""
    data = read_json(C.OWNER_REQUESTS_FILE, {"requests": []})
    for r in data.get("requests", []):
        if r.get("date") == date and r.get("topic"):
            if slugify(r["topic"]) in used_slugs:
                continue
            return {"topic": r["topic"], "type": r.get("type", "unsolved_mystery")}
    return None


def pick_topic() -> dict:
    """Pick the next unused topic. Falls back to model-proposed if bank exhausted."""
    bank = _load_bank()
    used = _load_used()
    used_slugs = _used_names(used)

    # PRIORITY 1: an owner-booked topic for today's date.
    owner = _owner_request_for(today_str(), used_slugs)
    if owner:
        chosen = owner
        log.info("Using OWNER-requested topic for %s: %s", today_str(), owner["topic"])
    else:
        # PRIORITY 2+: newest SEO-report topics first (they carry an 'added' date),
        # then older unused ones, then the seed bank (no 'added' date). A topic is
        # only removed from rotation once it has been USED (used_topics.json), so
        # any topic never turned into a video stays usable forever.
        candidates = [t for t in bank if slugify(t["topic"]) not in used_slugs]
        if candidates:
            candidates.sort(key=lambda t: t.get("added", ""), reverse=True)
            chosen = candidates[0]
        else:
            log.warning("Topic bank exhausted -- asking model for a fresh idea.")
            chosen = _fresh_from_model(used_slugs) or {
                "topic": f"Unsolved Mystery #{len(used)+1}",
                "type": "unsolved_mystery",
            }

    return {
        "topic": chosen["topic"],
        "slug": slugify(chosen["topic"]),
        "type": chosen.get("type", "unsolved_mystery"),
        "date": today_str(),
    }


def _fresh_from_model(used_slugs: set[str]) -> dict | None:
    """Ask the script LLM for one new mystery idea not already used."""
    try:
        from .script import call_llm  # lazy import to avoid cycle
        prompt = (
            "Give ONE fresh, real, famous unsolved mystery / true story / "
            "mind-blowing fact topic for a Hinglish YouTube channel. "
            "Return STRICT JSON: {\"topic\": \"...\", \"type\": "
            "\"unsolved_mystery|true_story|mind_blowing_fact\"}. "
            "Avoid these slugs: " + ", ".join(sorted(used_slugs))
        )
        from .utils import extract_json
        data = extract_json(call_llm(prompt))
        if data.get("topic") and slugify(data["topic"]) not in used_slugs:
            # persist into the bank for future runs
            bank_data = read_json(C.TOPICS_FILE, {"topics": []})
            bank_data.setdefault("topics", []).append(data)
            write_json(C.TOPICS_FILE, bank_data)
            return data
    except Exception as e:  # noqa: BLE001
        log.warning("fresh_from_model failed: %s", e)
    return None


def mark_used(state: dict) -> None:
    data = read_json(C.USED_TOPICS_FILE, {"used": []})
    data.setdefault("used", []).append(
        {"topic": state["topic"], "slug": state["slug"], "date": state["date"]}
    )
    write_json(C.USED_TOPICS_FILE, data)


def save_state(state: dict) -> None:
    write_json(C.STATE_FILE, state)


def load_state() -> dict:
    return read_json(C.STATE_FILE, {})


def write_today_topic_file(state: dict) -> None:
    C.THUMBS_DIR.mkdir(parents=True, exist_ok=True)
    txt = (
        f"TOPIC: {state['topic']}\n"
        f"SLUG: {state['slug']}\n"
        f"DATE: {state['date']}\n"
        f"THUMBNAIL FILENAME TO DROP: {state['slug']}.png  (1280x720)\n"
    )
    (C.THUMBS_DIR / "TODAY_TOPIC.txt").write_text(txt, encoding="utf-8")


def push_to_drive(state: dict) -> None:
    """Copy TODAY_TOPIC.txt to the shared Drive folder via rclone (if configured)."""
    if not C.RCLONE_CONF or not have("rclone"):
        log.info("rclone not configured/installed — skipping Drive push (repo folder still used).")
        return
    try:
        src = C.THUMBS_DIR / "TODAY_TOPIC.txt"
        run(["rclone", "copy", str(src), C.RCLONE_REMOTE], check=True)
        log.info("Pushed TODAY_TOPIC.txt to %s", C.RCLONE_REMOTE)
    except Exception as e:  # noqa: BLE001
        log.warning("Drive push failed (non-fatal): %s", e)


def _email_topic(state: dict) -> None:
    subject = f"Aaj ka topic: {state['topic']}"
    body = (
        f"Aaj ka RAAZ FILES topic: {state['topic']}\n"
        f"Slug: {state['slug']}\n\n"
        f"Agar custom thumbnail banana hai to is naam se 1280x720 PNG "
        f"folder me daal do:\n    {state['slug']}.png  (ya {state['date']}.png)\n\n"
        f"Nahi daala to 4:30 PM par AI khud bana lega. Sab automatic hai.\n"
    )
    notify.email_owner(subject, body)


def announce() -> dict:
    # IDEMPOTENT: if today's topic is already chosen, re-announce the SAME one
    # instead of picking (and burning) a new topic. So running morning-topic
    # twice in a day is safe -- it will NOT waste an extra topic.
    existing = load_state()
    if existing.get("date") == today_str() and existing.get("topic"):
        log.info("Topic already chosen for %s: %s -- re-announcing same (no new pick)",
                 today_str(), existing["topic"])
        write_today_topic_file(existing)
        push_to_drive(existing)
        _email_topic(existing)
        return existing

    state = pick_topic()
    log.info("Today's topic: %s (%s)", state["topic"], state["slug"])
    write_today_topic_file(state)
    save_state(state)
    mark_used(state)
    push_to_drive(state)
    _email_topic(state)
    return state


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--announce", action="store_true")
    ap.add_argument("--show", action="store_true")
    args = ap.parse_args(argv)

    if args.show:
        print(load_state())
        return
    # default action is announce
    announce()


if __name__ == "__main__":
    main(sys.argv[1:])
