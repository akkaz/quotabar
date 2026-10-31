import {accentContrast, age, countdown, expired, panelWindows, parseHexColor, percent, quotaMeter,
    readableAccent, resolveClaudeWindowMode} from '../extension/presentation.js';

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
equal(panelWindows('claude', [week, fiveHour], 'five-hour')[0].id, 'five_hour');
equal(panelWindows('claude', [week, fiveHour], 'weekly')[0].id, 'seven_day');
equal(panelWindows('claude', [fiveHour], 'weekly').length, 0);
equal(panelWindows('claude', [week], 'five-hour').length, 0);
equal(panelWindows('claude', [week], 'weekly').length, 1);
equal(resolveClaudeWindowMode(null, false), 'five-hour');
equal(resolveClaudeWindowMode(null, true), 'both');
equal(resolveClaudeWindowMode('weekly', false), 'weekly');
equal(resolveClaudeWindowMode('both', false), 'both');
equal(resolveClaudeWindowMode('invalid', false), 'five-hour');
equal(parseHexColor('rgba(0,0,0,0)'), null);
equal(parseHexColor('#123456; color: red'), null);
equal(parseHexColor('#123'), null);
equal(parseHexColor(null), null);
equal(parseHexColor('#FFFFFF').join(','), '1,1,1');
equal(parseHexColor('#000000').join(','), '0,0,0');
equal(quotaMeter(20, false, true, {green: '#0088ff'}).color.join(','), parseHexColor('#0088ff').join(','));
equal(quotaMeter(20, false, false, {green: '#0088ff'}).color.join(','), parseHexColor('#0088ff').join(','));
equal(quotaMeter(60, false, true, {amber: '#ff00ff'}).color.join(','), '1,0,1');
equal(quotaMeter(90, true, true, {red: '#000000'}).color.join(','), '0,0,0');
equal(quotaMeter(20, false, true, {green: 'bad'}).color.join(','), quotaMeter(20).color.join(','));
for (const background of [[0.21, 0.21, 0.22], [1, 1, 1], [0.5, 0.5, 0.5]]) {
    for (const hex of ['#000000', '#ffffff', '#0088ff', '#ff00ff', '#57e38a', '#f5c44a', '#ff7869']) {
        const color = parseHexColor(hex);
        const surface = color.map((c, i) => c * 0.07 + background[i] * 0.93);
        equal(accentContrast(readableAccent(color, background), surface) >= 4.5, true);
    }
}
equal(panelWindows('codex', [fiveHour, week]).map(w => w.id).join(','), 'seven_day');
equal(panelWindows('codex', [fiveHour]).length, 1);
equal(panelWindows('codex', []).length, 0);
print(`${count} presentation checks: OK`);
