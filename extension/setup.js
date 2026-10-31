import Adw from 'gi://Adw';
import GLib from 'gi://GLib';
import {fillPreferences, settingsFromDirectory} from './ui.js';

const helper = ARGV[0];
if (!helper)
    throw new Error('Avvia le impostazioni con quotabar settings');
const directory = GLib.path_get_dirname(helper);
const app = new Adw.Application({application_id: 'dev.akkaz.QuotaBar'});
app.connect('activate', () => {
    if (app.active_window) {
        app.active_window.present();
        return;
    }
    const window = new Adw.PreferencesWindow({application: app, title: 'QuotaBar'});
    fillPreferences(window, settingsFromDirectory(directory), helper);
    window.present();
});
app.run([]);
