// Pure presentation helpers, shared with the native tests.
const meterColors = {
    green: {dark: [0.34, 0.89, 0.54], light: [0.09, 0.45, 0.26]},
    amber: {dark: [0.96, 0.77, 0.29], light: [0.62, 0.39, 0]},
    red: {dark: [1, 0.47, 0.41], light: [0.78, 0.23, 0.20]},
};

export function quotaMeter(used, displayRemaining = false, darkSurface = true) {
    if (!Number.isFinite(used))
        return null;
    const consumed = Math.max(0, Math.min(100, used));
    const left = 100 - consumed;
    const tone = left <= 20 ? 'red' : left <= 50 ? 'amber' : 'green';
    return {fill: displayRemaining ? left : consumed, remaining: left, tone,
        color: meterColors[tone][darkSurface ? 'dark' : 'light']};
}

export function panelWindows(provider, windows, showWeekly = true) {
    const sorted = [...(Array.isArray(windows) ? windows : [])]
        .sort((a, b) => (a.duration_minutes ?? Infinity) - (b.duration_minutes ?? Infinity));
    if (provider === 'codex') {
        // Prefer its weekly quota, while retaining the real available window
        // for accounts whose plan has no weekly bucket.
        const weekly = sorted.find(item => item.duration_minutes >= 1440);
        return weekly ? [weekly] : sorted.slice(0, 1);
    }
    return sorted.slice(0, showWeekly ? 2 : 1);
}

export function countdown(reset, now = Date.now() / 1000) {
    if (!Number.isFinite(reset))
        return '—';
    const seconds = reset - now;
    if (seconds <= 0)
        return 'in attesa';
    const minutes = Math.ceil(seconds / 60);
    const days = Math.floor(minutes / 1440);
    const hours = Math.floor((minutes % 1440) / 60);
    const mins = minutes % 60;
    if (days > 0)
        return `${days}g ${hours}h`;
    if (hours > 0)
        return `${hours}h ${mins}m`;
    return `${mins}m`;
}

export function expired(item, now = Date.now() / 1000) {
    return Number.isFinite(item.resets_at) && item.resets_at <= now;
}

export function percent(item, remaining = false) {
    if (!Number.isFinite(item?.used))
        return '—';
    return `${Math.round(remaining ? 100 - item.used : item.used)}%`;
}

export function age(timestamp, now = Date.now() / 1000) {
    if (!Number.isFinite(timestamp))
        return 'mai aggiornato';
    const seconds = Math.max(0, now - timestamp);
    if (seconds < 60)
        return 'aggiornato ora';
    if (seconds < 3600)
        return `aggiornato ${Math.floor(seconds / 60)} min fa`;
    return `aggiornato ${Math.floor(seconds / 3600)} h fa`;
}
