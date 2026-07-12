"""fallback.py -- run a chain of providers: try primary -> except -> backup.

Per-attempt failures are logged at DEBUG (expected provider-hopping is noisy
and harmless); only the final SUCCESS is logged at INFO, and a total failure
(every provider down) is logged at WARNING.
"""
from __future__ import annotations

from typing import Callable

from .utils import get_logger

log = get_logger("fallback")

# Records which provider actually served each stage (for qa_report).
USED_PROVIDERS: dict[str, str] = {}


def try_chain(stage: str, providers: list[tuple[str, Callable]]):
    """Try each (name, fn) in order. Return the first truthy result.

    Raises RuntimeError only if every provider fails.
    """
    errors = []
    for name, fn in providers:
        if fn is None:
            continue
        try:
            result = fn()
            if result:
                USED_PROVIDERS[stage] = name
                log.info("[%s] via %s", stage, name)
                return result
            errors.append(f"{name}: returned empty")
            log.debug("[%s] %s returned empty, trying next", stage, name)
        except Exception as e:  # noqa: BLE001
            errors.append(f"{name}: {e}")
            log.debug("[%s] %s failed: %s", stage, name, e)
    log.warning("[%s] all providers failed -> %s", stage, errors)
    raise RuntimeError(f"[{stage}] all providers failed -> {errors}")
