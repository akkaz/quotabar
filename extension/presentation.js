// Pure presentation helpers, shared with the native tests.
const meterColors = {
    green: {dark: [0.34, 0.89, 0.54], light: [0.09, 0.45, 0.26]},
    amber: {dark: [0.96, 0.77, 0.29], light: [0.62, 0.39, 0]},
    red: {dark: [1, 0.47, 0.41], light: [0.78, 0.23, 0.20]},
};

export function parseHexColor(value) {
    if (typeof value !== 'string' || !/^#[\da-f]{6}$/i.test(value))
        return null;
    return [1, 3, 5].map(offset => parseInt(value.slice(offset, offset + 2), 16) / 255);
}

export function quotaMeter(used, displayRemaining = false, darkSurface = true, palette = {}) {
    if (!Number.isFinite(used))
        return null;
    const consumed = Math.max(0, Math.min(100, used));
    const left = 100 - consumed;
    const tone = left <= 20 ? 'red' : left <= 50 ? 'amber' : 'green';
    return {fill: displayRemaining ? left : consumed, remaining: left, tone,
        color: parseHexColor(palette[tone]) ?? meterColors[tone][darkSurface ? 'dark' : 'light']};
}

export function resolveClaudeWindowMode(value, legacyShowWeekly = true) {
    return ['both', 'five-hour', 'weekly'].includes(value)
        ? value : legacyShowWeekly ? 'both' : 'five-hour';
}

// Keep numerical text readable even for a custom black/white or very dark color.
export function accentContrast(color, background) {
    const luminance = rgb => rgb.map(c => c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4)
        .reduce((total, c, i) => total + c * [0.2126, 0.7152, 0.0722][i], 0);
    const [low, high] = [luminance(color), luminance(background)].sort((a, b) => a - b);
    return (high + 0.05) / (low + 0.05);
}

export function readableAccent(color, background) {
    const surface = color.map((c, i) => c * 0.07 + background[i] * 0.93);
    if (accentContrast(color, surface) >= 4.5)
        return color;
    const target = accentContrast([1, 1, 1], surface) > accentContrast([0, 0, 0], surface) ? 1 : 0;
    for (let mix = 0.05; mix <= 1.001; mix += 0.05) {
        const adjusted = color.map(c => c * (1 - mix) + target * mix);
        if (accentContrast(adjusted, surface) >= 4.6)
            return adjusted;
    }
    return [target, target, target];
}

export function panelWindows(provider, windows, claudeMode = 'both') {
    const sorted = [...(Array.isArray(windows) ? windows : [])]
        .sort((a, b) => (a.duration_minutes ?? Infinity) - (b.duration_minutes ?? Infinity));
    if (provider === 'codex') {
        // Prefer its weekly quota, while retaining the real available window
        // for accounts whose plan has no weekly bucket.
        const weekly = sorted.find(item => item.duration_minutes >= 1440);
        return weekly ? [weekly] : sorted.slice(0, 1);
    }
    if (claudeMode === 'weekly')
        return sorted.filter(item => item.id === 'seven_day' || item.duration_minutes >= 1440).slice(0, 1);
    if (claudeMode === 'five-hour')
        return sorted.filter(item => item.id === 'five_hour' || item.duration_minutes === 300).slice(0, 1);
    return sorted.slice(0, 2);
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
