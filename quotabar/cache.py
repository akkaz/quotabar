"""Private, atomic cache of usage numbers. Credentials never enter this module."""

import fcntl
import json
import os
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from .providers import ProviderError, fetch_claude, fetch_codex


def cache_directory():
    base = Path(os.environ.get("XDG_CACHE_HOME", str(Path.home() / ".cache")))
    path = base / "quotabar"
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


def update_provider(name, old, fetch, interval, refresh, now):
    old = old if isinstance(old, dict) else {}
    observed = old.get("observed_at") or 0
    # Manual refresh respects provider backoff and a minimum request gap.
    minimum = 60 if name == "claude" else 15
    due = max(old.get("retry_at", 0), observed + (minimum if refresh else interval))
    if now < due:
        return old or {"status": "waiting", "windows": [], "extra": []}
    try:
        result = fetch()
        return {**result, "status": "ok", "observed_at": time.time(),
                "attempted_at": now, "failures": 0, "retry_at": 0}
    except Exception as error:
        if not isinstance(error, ProviderError):
            error = ProviderError("Lettura non riuscita. Aggiorna la CLI e riprova.", "internal")
        failures = min(7, int(old.get("failures", 0)) + 1)
        delay = max(error.retry_after, min(3600, interval * (2 ** (failures - 1))))
        # Preserve the last successful numbers, visibly marked as old data.
        return {**old, "status": "error", "windows": old.get("windows", []),
                "extra": old.get("extra", []), "error": str(error), "error_kind": error.kind,
                "attempted_at": now, "failures": failures, "retry_at": now + delay}


def snapshot(refresh=False, codex_interval=60, claude_interval=180, only=None):
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
                    return {"version": 1, "generated_at": time.time(), "providers": state}
                time.sleep(0.1)
        state = read_cache(state_file)
        now = time.time()
        jobs = {"codex": (fetch_codex, max(30, codex_interval)),
                "claude": (fetch_claude, max(60, claude_interval))}
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = {name: pool.submit(update_provider, name, state.get(name), fetch,
                                        interval, refresh, now)
                       for name, (fetch, interval) in jobs.items() if only is None or name in only}
            for name, future in pending.items():
                state[name] = future.result()
        atomic_write(state_file, state)
        return {"version": 1, "generated_at": time.time(),
                "providers": {name: state[name] for name in jobs if name in state and (only is None or name in only)}}
