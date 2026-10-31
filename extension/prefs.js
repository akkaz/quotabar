import {ExtensionPreferences} from 'resource:///org/gnome/Shell/Extensions/js/extensions/prefs.js';
import {fillPreferences} from './ui.js';

export default class QuotaBarPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        fillPreferences(window, this.getSettings(), `${this.path}/helper.py`);
    }
}
