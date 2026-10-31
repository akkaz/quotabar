import Adw from 'gi://Adw';
import Gio from 'gi://Gio';
import Gdk from 'gi://Gdk';
import GLib from 'gi://GLib';
import Gtk from 'gi://Gtk';
import {age, parseHexColor, percent, quotaMeter, resolveClaudeWindowMode} from './presentation.js';

const UUID = 'quotabar@akkaz.dev';

export function settingsFromDirectory(directory) {
    const source = Gio.SettingsSchemaSource.new_from_directory(
        `${directory}/schemas`, Gio.SettingsSchemaSource.get_default(), false);
    const schema = source.lookup('org.gnome.shell.extensions.quotabar', false);
    if (!schema)
        throw new Error('Schema QuotaBar non installato');
    return new Gio.Settings({settings_schema: schema});
}

function toggle(group, settings, key, title, subtitle = '') {
    const row = new Adw.SwitchRow({title, subtitle, use_markup: false});
    settings.bind(key, row, 'active', Gio.SettingsBindFlags.DEFAULT);
    group.add(row);
    return row;
}

function spin(group, settings, key, title, subtitle, minimum, maximum, step) {
    const row = new Adw.ActionRow({title, subtitle, use_markup: false});
    const input = Gtk.SpinButton.new_with_range(minimum, maximum, step);
    input.valign = Gtk.Align.CENTER;
    input.numeric = true;
    row.add_suffix(input);
    row.activatable_widget = input;
    settings.bind(key, input, 'value', Gio.SettingsBindFlags.DEFAULT);
    group.add(row);
}

export function fillPreferences(window, settings, helper) {
    window.set_default_size(620, 760);
    window.add_css_class('quotabar-preferences');
    const contrast = new Gtk.CssProvider();
    contrast.load_from_string(`
        .quotabar-preferences .subtitle,
        .quotabar-preferences .dim-label,
        .quotabar-preferences .dimmed {
            color: inherit;
            opacity: 0.8;
        }
    `);
    const display = window.get_display();
    Gtk.StyleContext.add_provider_for_display(display, contrast, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION);
    const cancellable = new Gio.Cancellable();
    let closed = false;
    let reading = false;
    let readAgain = false;
    const cleanups = [];
    window.connect('close-request', () => {
        closed = true;
        cancellable.cancel();
        for (const cleanup of cleanups)
            cleanup();
        Gtk.StyleContext.remove_provider_for_display(display, contrast);
        return false;
    });
    const toast = message => window.add_toast(new Adw.Toast({title: message, timeout: 5}));
    const run = (args, done) => {
        try {
            const proc = Gio.Subprocess.new(['/usr/bin/python3', helper, ...args],
                Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
            proc.communicate_utf8_async(null, cancellable, (process, result) => {
                try {
                    const [, stdout, stderr] = process.communicate_utf8_finish(result);
                    if (!closed)
                        done(process.get_successful(), stdout, stderr);
                } catch (_error) {
                    if (!closed)
                        done(false, '', 'Operazione non riuscita. Riprova.');
                }
            });
        } catch (_error) {
            done(false, '', 'Impossibile avviare l’helper. Verifica l’installazione.');
        }
    };

    const page = new Adw.PreferencesPage({title: 'Generali', name: 'general', icon_name: 'utilities-system-monitor-symbolic'});
    window.add(page);
    const activation = new Adw.PreferencesGroup({title: 'Nella barra, quando serve',
        description: 'Barrette, quote e tempi di reset accanto agli indicatori di GNOME. Compatibile con GNOME 48.'});
    const shell = new Gio.Settings({schema_id: 'org.gnome.shell'});
    const auto = new Adw.SwitchRow({title: 'Mostra nel pannello e ai prossimi accessi',
        subtitle: 'Alla prima installazione può servire uscire dalla sessione e rientrare.', use_markup: false});
    const enabled = () => shell.get_strv('enabled-extensions').includes(UUID)
        && !shell.get_strv('disabled-extensions').includes(UUID)
        && !shell.get_boolean('disable-user-extensions');
    auto.active = enabled();
    auto.connect('notify::active', () => {
        if (auto.active === enabled())
            return;
        if (auto.active && shell.get_boolean('disable-user-extensions')) {
            toast('Le estensioni GNOME sono disattivate. Riattivale nell’app Estensioni.');
            auto.active = false;
            return;
        }
        const on = new Set(shell.get_strv('enabled-extensions'));
        const off = new Set(shell.get_strv('disabled-extensions'));
        if (auto.active) {
            on.add(UUID);
            off.delete(UUID);
        } else {
            on.delete(UUID);
            off.add(UUID);
        }
        shell.set_strv('disabled-extensions', [...off]);
        shell.set_strv('enabled-extensions', [...on]);
        toast(auto.active ? 'Attivato. Se la barra non compare, esci dalla sessione e rientra.' : 'QuotaBar rimosso dal pannello.');
    });
    activation.add(auto);
    page.add(activation);

    const accounts = new Adw.PreferencesGroup({title: 'Account',
        description: 'Usa il tuo abbonamento. Il login si apre nel browser tramite la CLI ufficiale, in una finestra di terminale.'});
    const rows = {};
    for (const [name, title] of [['claude', 'Claude'], ['codex', 'Codex / ChatGPT']]) {
        const row = new Adw.ActionRow({title, subtitle: 'Verifica account in corso…', use_markup: false});
        const button = new Gtk.Button({label: 'Collega', valign: Gtk.Align.CENTER});
        button.connect('clicked', () => {
            run(['login', name], (success, _output, error) => {
                toast(success ? 'Completa il login nel browser, poi aggiorna le quote.' : error.trim());
            });
        });
        row.add_suffix(button);
        accounts.add(row);
        rows[name] = row;
    }
    const refreshRow = new Adw.ActionRow({title: 'Dati aggiornati',
        subtitle: 'Le letture condividono la cache con il pannello.', use_markup: false});
    const refresh = new Gtk.Button({label: 'Aggiorna quote', valign: Gtk.Align.CENTER});
    refreshRow.add_suffix(refresh);
    accounts.add(refreshRow);
    page.add(accounts);
    const read = (force = false) => {
        if (reading) {
            readAgain = true;
            return;
        }
        reading = true;
        refresh.sensitive = false;
        const args = ['snapshot', '--codex-interval', String(settings.get_int('codex-interval')),
            '--claude-interval', String(settings.get_int('claude-interval'))];
        if (force)
            args.push('--refresh');
        const requestedDemo = settings.get_boolean('demo-mode');
        if (requestedDemo)
            args.push('--demo');
        run(args, (success, output, error) => {
            reading = false;
            refresh.sensitive = true;
            if (requestedDemo !== settings.get_boolean('demo-mode') || readAgain) {
                readAgain = false;
                read();
                return;
            }
            if (!success) {
                toast(error.trim() || 'Impossibile leggere le quote. Riprova.');
                for (const row of Object.values(rows))
                    row.subtitle = 'Lettura non riuscita. Verifica l’installazione.';
                return;
            }
            try {
                const data = JSON.parse(output);
                for (const [name, row] of Object.entries(rows)) {
                    const provider = data.providers[name];
                    if (provider?.status === 'error')
                        row.subtitle = provider.error;
                    else if (provider?.windows?.length)
                        row.subtitle = `${data.demo ? 'Dati dimostrativi · ' : ''}${provider.windows.map(w => `${w.label}: ${percent(w)} usato`).join(' · ')}\n${age(provider.observed_at)}`;
                    else
                        row.subtitle = 'Nessuna quota disponibile. Collega un abbonamento.';
                }
            } catch (_error) {
                toast('Risposta non valida. Verifica l’installazione.');
            }
        });
    };
    refresh.connect('clicked', () => read(true));

    const appearancePage = new Adw.PreferencesPage({title: 'Aspetto', name: 'appearance',
        icon_name: 'preferences-desktop-display-symbolic'});
    window.add(appearancePage);
    const appearance = new Adw.PreferencesGroup({title: 'Come appare'});
    toggle(appearance, settings, 'show-claude', 'Mostra Claude');
    toggle(appearance, settings, 'show-codex', 'Mostra Codex');
    toggle(appearance, settings, 'show-bars', 'Barrette nel pannello');
    toggle(appearance, settings, 'show-countdown', 'Tempo al reset');
    const modes = ['both', 'five-hour', 'weekly'];
    const selectedMode = () => modes.indexOf(resolveClaudeWindowMode(
        settings.get_user_value('claude-window')?.deep_unpack(), settings.get_boolean('show-weekly')));
    const claudeWindow = new Adw.ComboRow({title: 'Limiti Claude nel pannello',
        subtitle: 'Il menu al clic conserva tutti i limiti disponibili.', use_markup: false,
        model: Gtk.StringList.new(['5 ore e settimana', 'Solo 5 ore', 'Solo settimana']),
        selected: selectedMode()});
    claudeWindow.connect('notify::selected', () => {
        const mode = modes[claudeWindow.selected];
        if (mode && claudeWindow.selected !== selectedMode())
            settings.set_string('claude-window', mode);
    });
    const modeSignal = settings.connect('changed::claude-window', () => { claudeWindow.selected = selectedMode(); });
    cleanups.push(() => settings.disconnect(modeSignal));
    const legacySignal = settings.connect('changed::show-weekly', () => { claudeWindow.selected = selectedMode(); });
    cleanups.push(() => settings.disconnect(legacySignal));
    settings.bind('show-claude', claudeWindow, 'sensitive', Gio.SettingsBindFlags.GET);
    appearance.add(claudeWindow);
    toggle(appearance, settings, 'provider-logos', 'Loghi dei provider',
        'Al posto dei nomi nel pannello.');
    toggle(appearance, settings, 'remaining', 'Mostra la percentuale rimanente',
        'Il menu mostra sempre la quota usata, come nelle pagine dei provider.');
    const compact = toggle(appearance, settings, 'compact', 'Nomi compatti', 'Cl e Cx quando i loghi sono disattivati.');
    settings.bind('provider-logos', compact, 'sensitive',
        Gio.SettingsBindFlags.GET | Gio.SettingsBindFlags.INVERT_BOOLEAN);
    const positions = ['right', 'center', 'left'];
    const position = new Adw.ComboRow({title: 'Posizione',
        model: Gtk.StringList.new(['Accanto agli indicatori', 'Accanto all’orologio', 'A sinistra']),
        selected: Math.max(0, positions.indexOf(settings.get_string('position')))});
    position.connect('notify::selected', () => settings.set_string('position', positions[position.selected]));
    appearance.add(position);
    appearancePage.add(appearance);

    const colors = new Adw.PreferencesGroup({title: 'Colori delle quote',
        description: 'Gli stessi colori nel pannello e nel menu. La percentuale rimanente determina lo stato; il testo viene adattato per restare leggibile.'});
    const styleManager = Adw.StyleManager.get_default();
    const colorRows = [];
    for (const [key, used, title, threshold] of [
        ['color-available', 0, 'Quota disponibile', 'Oltre il 50% rimanente'],
        ['color-warning', 60, 'Attenzione', 'Dal 50% fino a oltre il 20% rimanente'],
        ['color-critical', 90, 'Quasi esaurita', '20% rimanente o meno'],
    ]) {
        const row = new Adw.ActionRow({title, use_markup: false});
        const chooser = new Gtk.ColorDialogButton({valign: Gtk.Align.CENTER,
            dialog: new Gtk.ColorDialog({title: `Colore · ${title}`, with_alpha: false})});
        chooser.update_property([Gtk.AccessibleProperty.LABEL], [`Colore: ${title}`]);
        let syncing = false;
        const sync = () => {
            syncing = true;
            const custom = settings.get_string(key);
            const rgb = parseHexColor(custom) ?? quotaMeter(used, false, styleManager.dark).color;
            chooser.rgba = new Gdk.RGBA({red: rgb[0], green: rgb[1], blue: rgb[2], alpha: 1});
            row.subtitle = `${threshold} · ${parseHexColor(custom) ? custom.toUpperCase() : 'Automatico'}`;
            syncing = false;
        };
        chooser.connect('notify::rgba', () => {
            if (syncing)
                return;
            const rgba = chooser.rgba;
            const hex = '#' + [rgba.red, rgba.green, rgba.blue]
                .map(channel => Math.round(channel * 255).toString(16).padStart(2, '0')).join('');
            if (settings.get_string(key) !== hex)
                settings.set_string(key, hex);
        });
        row.add_suffix(chooser);
        row.activatable_widget = chooser;
        const colorSignal = settings.connect(`changed::${key}`, sync);
        cleanups.push(() => settings.disconnect(colorSignal));
        sync();
        colorRows.push(sync);
        colors.add(row);
    }
    const themeSignal = styleManager.connect('notify::dark', () => colorRows.forEach(sync => sync()));
    cleanups.push(() => styleManager.disconnect(themeSignal));
    const resetRow = new Adw.ActionRow({title: 'Ripristina colori automatici',
        subtitle: 'Torna a verde, giallo e rosso, adattati al tema.', use_markup: false});
    const resetColors = new Gtk.Button({label: 'Ripristina', valign: Gtk.Align.CENTER});
    resetColors.connect('clicked', () => {
        for (const key of ['color-available', 'color-warning', 'color-critical'])
            settings.reset(key);
        toast('Colori automatici ripristinati.');
    });
    resetRow.add_suffix(resetColors);
    colors.add(resetRow);
    appearancePage.add(colors);

    const polling = new Adw.PreferencesGroup({title: 'Aggiornamento automatico',
        description: 'Il conto alla rovescia è locale. Le quote vengono lette periodicamente, anche con le CLI chiuse. In caso di errori gli intervalli aumentano.'});
    spin(polling, settings, 'codex-interval', 'Codex · secondi', 'Protocollo ufficiale app-server.', 30, 900, 30);
    spin(polling, settings, 'claude-interval', 'Claude · secondi',
        'Endpoint non documentato. Consigliati almeno 180 secondi.', 60, 1800, 60);
    const session = new Adw.ActionRow({title: 'Sessione Claude scaduta?',
        subtitle: 'Apri Claude Code o ripeti il login. QuotaBar legge le credenziali della CLI e non le modifica.', use_markup: false});
    polling.add(session);
    page.add(polling);

    const tryIt = new Adw.PreferencesGroup({title: 'Prova senza account'});
    const demo = toggle(tryIt, settings, 'demo-mode', 'Modalità dimostrativa',
        'Numeri fittizi, indicati come DEMO. Non contatta i provider.');
    demo.connect('notify::active', () => read());
    page.add(tryIt);
    read();
}
