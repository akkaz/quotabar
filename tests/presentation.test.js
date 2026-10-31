import {age, countdown, expired, panelWindows, percent, quotaMeter} from '../extension/presentation.js';

let count = 0;
function equal(actual, expected) {
    count++;
    if (actual !== expected)
        throw new Error(`${JSON.stringify(actual)} != ${JSON.stringify(expected)}`);
}
equal(countdown(14320, 1000), '3h 42m');
equal(countdown(418600, 1000), '4g 20h');
equal(countdown(1030, 1000), '1m');
equal(countdown(1000, 1000), 'in attesa');
equal(countdown(null, 1000), '—');
equal(expired({resets_at: 900}, 1000), true);
equal(expired({resets_at: null}, 1000), false);
equal(percent({used: 0}), '0%');
equal(percent({used: 28}, true), '72%');
equal(percent({}), '—');
equal(age(null, 1000), 'mai aggiornato');
equal(age(1000, 1059), 'aggiornato ora');
equal(age(1000, 1120), 'aggiornato 2 min fa');
equal(quotaMeter(0).tone, 'green');
equal(quotaMeter(49).tone, 'green');
equal(quotaMeter(50).tone, 'amber');
equal(quotaMeter(79).tone, 'amber');
equal(quotaMeter(80).tone, 'red');
equal(quotaMeter(100).tone, 'red');
equal(quotaMeter(85, true).tone, quotaMeter(85, false).tone);
equal(quotaMeter(85, true).fill, 15);
equal(quotaMeter(85, false).fill, 85);
equal(quotaMeter(null), null);
equal(quotaMeter(100, true).fill, 0);
const fiveHour = {id: 'five_hour', duration_minutes: 300};
const week = {id: 'seven_day', duration_minutes: 10080};
equal(panelWindows('claude', [week, fiveHour]).map(w => w.id).join(','), 'five_hour,seven_day');
equal(panelWindows('claude', [week, fiveHour], false).length, 1);
equal(panelWindows('codex', [fiveHour, week]).map(w => w.id).join(','), 'seven_day');
equal(panelWindows('codex', [fiveHour]).length, 1);
equal(panelWindows('codex', []).length, 0);
print(`${count} presentation checks: OK`);
