import {fillPreferences, settingsFromDirectory} from '../extension/ui.js';
if (typeof fillPreferences !== 'function' || typeof settingsFromDirectory !== 'function')
    throw new Error('Native preferences exports are missing');
print('GTK4 / Libadwaita module imports: OK');
