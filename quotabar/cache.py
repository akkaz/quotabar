"""Private, atomic cache of usage numbers. Credentials never enter this module."""

import fcntl
import json
import math
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .providers import ProviderError, fetch_claude, fetch_codex
from .model import number


def claude_auth_revision():
    """Observe CLI-owned credential renewal without reading or copying tokens."""
    directory = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
    try:
        info = (directory / ".credentials.json").stat()
        return f"{info.st_dev}:{info.st_ino}:{info.st_mtime_ns}:{info.st_size}"
    except OSError:
        return "unavailable"


def cache_directory(create=True):
    base = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    path = base / "quotabar"
    if create:
        path.mkdir(parents=True, exist_ok=True, mode=0o700)
        path.chmod(0o700)
    return path


def read_cache(path):
    try:
        result = json.loads(path.read_text())
        return result if isinstance(result, dict) else {}
    except (OSError, ValueError):
        return {}


def atomic_write(path, value):
    descriptor, name = tempfile.mkstemp(prefix=".usage-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            json.dump(value, stream, allow_nan=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def update_provider(name, old, fetch, interval, refresh, now, auth_revision=None):
    old = old if isinstance(old, dict) else {}
    # The official CLI may renew its login while we are backing off an auth
    # error. New credentials must be tried immediately, including old caches
    # written before credential revisions were tracked. Never bypass HTTP 429.
    if (auth_revision is not None and old.get("error_kind") == "auth"
            and old.get("auth_revision") != auth_revision):
        old = {**old, "retry_at": 0, "failures": 0}
    observed = old.get("observed_at") or 0
    # Manual refresh respects provider backoff and a minimum request gap.
    minimum = 60 if name == "claude" else 15
    due = max(old.get("retry_at", 0), observed + (minimum if refresh else interval))
    if now < due:
        return old or {"status": "waiting", "windows": [], "extra": []}
    try:
        result = fetch()
        return {**result, "status": "ok", "observed_at": time.time(),
                "attempted_at": now, "failures": 0, "retry_at": 0,
                **({"auth_revision": auth_revision} if auth_revision is not None else {})}
    except Exception as error:
        if not isinstance(error, ProviderError):
            error = ProviderError("Lettura non riuscita. Aggiorna la CLI e riprova.", "internal")
        failures = min(7, int(old.get("failures", 0)) + 1)
        delay = (60 if error.kind == "auth" else
                 max(error.retry_after, min(3600, interval * (2 ** (failures - 1)))))
        # Preserve last-good numbers privately; display_provider hides them.
        return {**old, "status": "error", "windows": old.get("windows", []),
                "extra": old.get("extra", []), "error": str(error), "error_kind": error.kind,
                "attempted_at": now, "failures": failures, "retry_at": now + delay,
                **({"auth_revision": auth_revision} if auth_revision is not None else {})}


def display_provider(data, interval, now):
    """A cached number must never masquerade as current account usage."""
    data = dict(data) if isinstance(data, dict) else {}
    data.pop("auth_revision", None)  # Internal cache bookkeeping only.
    observed = number(data.get("observed_at"))
    if data.get("status") == "ok" and (observed is None
            or observed > now + 60 or now - observed > interval * 2):
        data.update(status="error", error_kind="stale",
                    error="Quote non aggiornate. Attendi una nuova lettura dal provider.")
    if data.get("status") == "error" and data.get("error_kind") == "rate_limit":
        retry_at = number(data.get("retry_at")) or now
        remaining = max(0, math.ceil(retry_at - now))
        wait = (f"Riprovo tra {math.ceil(remaining / 60)} min." if remaining >= 60 else
                f"Riprovo tra {remaining} s." if remaining else "Riprovo a breve.")
        # Also clarifies caches written by older versions of the helper.
        data["error"] = f"Lettura quote in pausa (HTTP 429).\n{wait}"
    if data.get("status") != "ok":
        # Preserve last-good numbers privately for recovery, never emit them
        # as percentages to the panel or settings, including older extensions.
        data.update(windows=[], extra=[])
    else:
        for key in ("windows", "extra"):
            data[key] = [item for item in data.get(key, []) if isinstance(item, dict)
                         and (number(item.get("resets_at")) is None
                              or item["resets_at"] > now)]
    return data


def display_snapshot(state, jobs):
    now = time.time()
    return {"version": 1, "generated_at": now, "providers": {
        name: display_provider(state[name], interval, now)
        for name, (_, interval) in jobs.items() if name in state}}


def snapshot(refresh=False, codex_interval=60, claude_interval=180, only=None, cached_only=False):
    jobs = {"codex": (fetch_codex, max(30, codex_interval)),
            "claude": (fetch_claude, max(60, claude_interval))}
    if only is not None:
        jobs = {name: job for name, job in jobs.items() if name in only}
    if cached_only:
        # Preferences follow the panel's atomic cache without locks, writes or
        # extra provider requests, even while another helper is fetching.
        state = read_cache(cache_directory(create=False) / "usage.json")
        return display_snapshot(state, jobs)
    directory = cache_directory()
    state_file = directory / "usage.json"
    descriptor = os.open(directory / "usage.lock", os.O_CREAT | os.O_RDWR, 0o600)
    with os.fdopen(descriptor, "w") as lock:
        # Separate UI windows and shell ticks share the same cached requests.
        deadline = time.monotonic() + 5
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    state = read_cache(state_file)
                    return display_snapshot(state, jobs)
                time.sleep(0.1)
        state = read_cache(state_file)
        now = time.time()
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = {name: pool.submit(update_provider, name, state.get(name), fetch,
                                        interval, refresh, now,
                                        claude_auth_revision() if name == "claude" else None)
                       for name, (fetch, interval) in jobs.items()}
            for name, future in pending.items():
                state[name] = future.result()
        atomic_write(state_file, state)
        return display_snapshot(state, jobs)
