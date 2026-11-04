// Requires an isolated GNOME display. The helper and every value are synthetic.
import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import {fillPreferences, settingsFromDirectory} from '../extension/ui.js';

Adw.init();
const temporary = GLib.dir_make_tmp('quotabar-prefs-status-XXXXXX');
const helper = `${temporary}/helper.py`;
const calls = `${temporary}/calls.jsonl`;
GLib.file_set_contents(helper, `
import json,pathlib,sys,time
with pathlib.Path(__file__).with_name('calls.jsonl').open('a') as log:
    log.write(json.dumps(sys.argv[1:])+'\\n')
cached='--cached' in sys.argv
provider=({'status':'ok','observed_at':time.time(),'windows':[{'label':'7g','used':45}]} if cached else
          {'status':'error','error_kind':'rate_limit','error':'Lettura quote in pausa (HTTP 429).\\nRiprovo tra 2 min.','windows':[]})
print(json.dumps({'version':1,'providers':{'claude':provider}}))
`);
const window = new Adw.PreferencesWindow({title: 'QuotaBar · synthetic status test'});
fillPreferences(window, settingsFromDirectory(ARGV[0]), helper);
window.present();
const loop = new GLib.MainLoop(null, false);
let failure = null;
let sawRateLimit = false;
let closed = false;
function findClaude(widget) {
    if (widget instanceof Adw.ActionRow && widget.title === 'Claude')
        return widget;
    for (let child = widget.get_first_child(); child; child = child.get_next_sibling()) {
        const row = findClaude(child);
        if (row)
            return row;
    }
    return null;
}
function readCalls() {
    const [, data] = GLib.file_get_contents(calls);
    return new TextDecoder().decode(data).trim().split('\n').map(line => JSON.parse(line));
}
const deadline = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 35, () => {
    failure = 'Preferences did not recover from the synthetic rate limit or stop polling on close';
    window.close();
    loop.quit();
    return GLib.SOURCE_REMOVE;
});
GLib.timeout_add(GLib.PRIORITY_DEFAULT, 50, () => {
    const row = findClaude(window);
    sawRateLimit ||= row?.subtitle.includes('HTTP 429');
    if (!sawRateLimit || !row?.subtitle.includes('45%'))
        return GLib.SOURCE_CONTINUE;
    const requests = readCalls();
    if (requests.length !== 2 || requests[0].includes('--cached') || !requests[1].includes('--cached'))
        failure = `Expected one initial read and one cache-only recovery, got ${JSON.stringify(requests)}`;
    closed = true;
    window.close();
    GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 11, () => {
        if (readCalls().length !== requests.length)
            failure = 'Preferences kept launching helpers after closing';
        GLib.source_remove(deadline);
        loop.quit();
        return GLib.SOURCE_REMOVE;
    });
    return GLib.SOURCE_REMOVE;
});
loop.run();
for (const path of [calls, helper, temporary])
    Gio.File.new_for_path(path).delete(null);
if (failure || !closed)
    throw new Error(failure || 'Preferences status test did not finish');
print('Native preferences: 429 -> recovered cache; no extra provider reads; polling stops on close: OK');
