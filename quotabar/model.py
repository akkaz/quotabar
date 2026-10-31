"""Provider responses -> a small, credential-free UI protocol."""

import math
from datetime import datetime


def number(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        return None
    return value if math.isfinite(value) else None


def timestamp(value):
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()
        except (ValueError, OverflowError):
            return None
    value = number(value)
    return value if value is not None and value > 0 else None


def duration_label(minutes):
    if not minutes:
        return "Quota"
    if minutes % 1440 == 0:
        return f"{minutes // 1440:g}g"
    if minutes % 60 == 0:
        return f"{minutes // 60:g}h"
    return f"{minutes:g}m"


def window(key, label, used, resets, minutes=None):
    used = number(used)
    if used is None:
        return None  # Missing is unknown, never zero.
    return {"id": key, "label": str(label)[:80],
            "used": min(100, max(0, used)), "resets_at": timestamp(resets),
            "duration_minutes": number(minutes)}


def codex_windows(bucket, prefix=""):
    result = []
    for key in ("primary", "secondary"):
        raw = bucket.get(key)
        if not isinstance(raw, dict):
            continue
        minutes = number(raw.get("windowDurationMins"))
        item = window(prefix + key, duration_label(minutes), raw.get("usedPercent"),
                      raw.get("resetsAt"), minutes)
        if item:
            result.append(item)
    return result


def normalize_codex(raw):
    bucket = raw.get("rateLimits") or {}
    buckets = raw.get("rateLimitsByLimitId") or {}
    if not bucket and isinstance(buckets, dict):
        bucket = buckets.get("codex") or next(iter(buckets.values()), {})
    if not isinstance(bucket, dict):
        bucket = {}
    windows = codex_windows(bucket)
    extra = []
    if isinstance(buckets, dict):
        for key, other in buckets.items():
            if not isinstance(other, dict) or key == bucket.get("limitId", "codex"):
                continue
            label = str(other.get("limitName") or key)[:80]
            for item in codex_windows(other, key + ":"):
                item["label"] = f"{label} · {item['label']}"
                extra.append(item)
    return {"windows": windows, "extra": extra, "plan": bucket.get("planType")}


def normalize_claude(raw, plan=None):
    windows, extra = [], []
    for key, label, minutes in (("five_hour", "5h", 300), ("seven_day", "7g", 10080)):
        item = raw.get(key)
        if isinstance(item, dict):
            item = window(key, label, item.get("utilization"), item.get("resets_at"), minutes)
            if item:
                windows.append(item)
    # The newer schema labels model windows in `limits`; prefer those over
    # opaque internal field names. Support the older named fields as well.
    limits = raw.get("limits") or []
    if isinstance(limits, list):
        for i, item in enumerate(limits):
            if not isinstance(item, dict):
                continue
            scope = item.get("scope") or {}
            model = scope.get("model") or {} if isinstance(scope, dict) else {}
            label = model.get("display_name") if isinstance(model, dict) else None
            if not isinstance(label, str) or not label.strip():
                continue
            minutes = 300 if item.get("group") == "session" else 10080
            item = window(f"model:{i}", f"{label} · {duration_label(minutes)}",
                          item.get("percent"), item.get("resets_at"), minutes)
            if item:
                extra.append(item)
    if not extra:
        for key, label in (("seven_day_opus", "Opus · 7g"), ("seven_day_sonnet", "Sonnet · 7g")):
            item = raw.get(key)
            if isinstance(item, dict):
                item = window(key, label, item.get("utilization"), item.get("resets_at"), 10080)
                if item:
                    extra.append(item)
    return {"windows": windows, "extra": extra, "plan": plan}
