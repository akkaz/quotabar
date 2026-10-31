import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Pango from 'gi://Pango';
import St from 'gi://St';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import {age, countdown, expired, panelWindows, percent, quotaMeter} from './presentation.js';

const names = {claude: 'Claude', codex: 'Codex'};

function label(text, style = '') {
    const widget = new St.Label({text, style_class: style, y_align: Clutter.ActorAlign.CENTER});
    widget.clutter_text.ellipsize = Pango.EllipsizeMode.NONE;
    return widget;
}

function darkSurface(widget) {
    const color = widget.get_theme_node().get_foreground_color();
    return (color.red * 0.2126 + color.green * 0.7152 + color.blue * 0.0722) > 128;
}

function bar(used, width = 38, height = 6, displayRemaining = false) {
    const area = new St.DrawingArea({width, height, y_align: Clutter.ActorAlign.CENTER});
    area.connect('repaint', widget => {
        const cr = widget.get_context();
        const [w, h] = widget.get_surface_size();
        const radius = h / 2;
        const pill = length => {
            cr.newSubPath();
            cr.arc(radius, radius, radius, Math.PI / 2, 3 * Math.PI / 2);
            cr.arc(Math.max(radius, length - radius), radius, radius, 3 * Math.PI / 2, Math.PI / 2);
            cr.closePath();
        };
        const color = widget.get_theme_node().get_foreground_color();
        const meter = quotaMeter(used, displayRemaining, darkSurface(widget));
        cr.setSourceRGBA(color.red / 255, color.green / 255, color.blue / 255, 0.18);
        pill(w);
        cr.fill();
        if (meter?.fill > 0) {
            cr.setSourceRGBA(...meter.color, 1);
            // Clip avoids an oversized rounded cap for values very near zero.
            cr.save();
            cr.rectangle(0, 0, meter.fill / 100 * w, h);
            cr.clip();
            pill(w);
            cr.fill();
            cr.restore();
        }
        cr.$dispose();
    });
    return area;
}

export default class QuotaBar extends Extension {
    enable() {
        this._generation = Symbol('enabled');
        this._settings = this.getSettings();
        this._cancellable = new Gio.Cancellable();
        this._data = null;
        this._process = null;
        this._message = null;
        this._button = new PanelMenu.Button(0.5, 'QuotaBar: quote Codex e Claude');
        this._box = new St.BoxLayout({style_class: 'qb-panel'});
        this._button.add_child(this._box);
        this._place();
        this._settingsId = this._settings.connect('changed', (_settings, key) => {
            if (key === 'position')
                this._place();
            if (['demo-mode', 'show-codex', 'show-claude', 'codex-interval', 'claude-interval'].includes(key)) {
                this._data = null;
                this._fetch();
            }
            this._render();
        });
        this._timer = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 10, () => {
            this._render(false);
            if (!this._lastFetch || Date.now() - this._lastFetch >= 30000)
                this._fetch();
            return GLib.SOURCE_CONTINUE;
        });
        this._menuId = this._button.menu.connect('open-state-changed', (_menu, open) => {
            if (open) {
                this._renderMenu();
                this._fetch();
            }
        });
        this._render();
        this._fetch();
    }

    _place() {
        // Register once; later changes only move the existing indicator.
        if (!Main.panel.statusArea[this.uuid])
            Main.panel.addToStatusArea(this.uuid, this._button, 0, this._settings.get_string('position'));
        else {
            const actor = this._button.container;
            actor.get_parent()?.remove_child(actor);
            const position = this._settings.get_string('position');
            const box = {left: Main.panel._leftBox, center: Main.panel._centerBox, right: Main.panel._rightBox}[position];
            box.insert_child_at_index(actor, 0);
        }
    }

    _fetch(refresh = false) {
        if (this._process) {
            this._queuedFetch = true;
            return;
        }
        const active = ['claude', 'codex'].filter(name => this._settings.get_boolean(`show-${name}`));
        if (active.length === 0) {
            this._data = {providers: {}};
            this._render();
            return;
        }
        const generation = this._generation;
        const args = ['/usr/bin/python3', `${this.path}/helper.py`, 'snapshot',
            '--only', active.length === 2 ? 'both' : active[0],
            '--codex-interval', String(this._settings.get_int('codex-interval')),
            '--claude-interval', String(this._settings.get_int('claude-interval'))];
        const requestedDemo = this._settings.get_boolean('demo-mode');
        if (requestedDemo)
            args.push('--demo');
        if (refresh)
            args.push('--refresh');
        try {
            const process = Gio.Subprocess.new(args, Gio.SubprocessFlags.STDOUT_PIPE | Gio.SubprocessFlags.STDERR_PIPE);
            this._process = process;
            this._lastFetch = Date.now();
            process.communicate_utf8_async(null, this._cancellable, (proc, result) => {
                let output;
                try {
                    [, output] = proc.communicate_utf8_finish(result);
                    if (this._generation !== generation)
                        return;
                    if (requestedDemo !== this._settings.get_boolean('demo-mode'))
                        return;
                    if (!proc.get_successful())
                        throw new Error('helper');
                    const data = JSON.parse(output);
                    if (data.version !== 1 || typeof data.providers !== 'object')
                        throw new Error('protocol');
                    const changed = JSON.stringify(data.providers) !== JSON.stringify(this._data?.providers)
                        || data.demo !== this._data?.demo || Boolean(this._message);
                    this._data = data;
                    this._message = null;
                    this._menuChanged = changed;
                } catch (_error) {
                    if (this._generation === generation)
                        this._message = 'Lettura non riuscita. Verifica l’installazione di QuotaBar.';
                } finally {
                    if (this._generation === generation) {
                        this._process = null;
                        this._render(this._menuChanged !== false);
                        this._menuChanged = null;
                        if (this._queuedFetch) {
                            this._queuedFetch = false;
                            this._fetch();
                        }
                    }
                }
            });
        } catch (_error) {
            this._process = null;
            this._message = 'Impossibile avviare QuotaBar. Verifica che Python 3 sia installato.';
            this._render();
        }
    }

    _render(rebuildMenu = true) {
        this._box.destroy_all_children();
        const remaining = this._settings.get_boolean('remaining');
        const demo = this._data?.demo === true;
        if (demo)
            this._box.add_child(label('DEMO', 'qb-demo'));
        const descriptions = [];
        for (const name of ['claude', 'codex']) {
            if (!this._settings.get_boolean(`show-${name}`))
                continue;
            const data = this._data?.providers?.[name];
            const group = new St.BoxLayout({style_class: 'qb-provider'});
            if (this._settings.get_boolean('provider-logos')) {
                group.add_child(new St.Icon({
                    gicon: new Gio.FileIcon({file: Gio.File.new_for_path(`${this.path}/icons/${name}-symbolic.svg`)}),
                    icon_size: 18,
                    style_class: `qb-provider-logo qb-logo-${name}`,
                    y_align: Clutter.ActorAlign.CENTER,
                    accessible_name: names[name],
                }));
            } else {
                const title = this._settings.get_boolean('compact') ? {claude: 'Cl', codex: 'Cx'}[name] : names[name];
                group.add_child(label(title, 'qb-provider-name'));
            }
            const windows = panelWindows(name, data?.windows, this._settings.get_boolean('show-weekly'));
            if (windows.length === 0)
                group.add_child(label(data?.status === 'error' ? '!' : '—', 'qb-muted'));
            let stale = data?.status === 'error' || Boolean(this._message);
            const interval = this._settings.get_int(`${name}-interval`);
            stale ||= data?.observed_at && Date.now() / 1000 - data.observed_at > interval * 2;
            for (let i = 0; i < windows.length; i++) {
                const item = windows[i];
                const old = expired(item);
                stale ||= old;
                const quota = new St.BoxLayout({style_class: 'qb-quota'});
                if (name === 'claude')
                    quota.add_child(label(item.label, 'qb-period'));
                if (this._settings.get_boolean('show-bars'))
                    quota.add_child(bar(item.used, 38, 6, remaining));
                quota.add_child(label(percent(item, remaining), old ? 'qb-muted' : 'qb-number'));
                if (this._settings.get_boolean('show-countdown'))
                    quota.add_child(label(countdown(item.resets_at), 'qb-muted'));
                quota.accessible_name = `${names[name]} ${item.label}: ${percent(item, remaining)} ${remaining ? 'rimanente' : 'usato'}`;
                group.add_child(quota);
                descriptions.push(`${names[name]} ${item.label}: ${percent(item, remaining)} ${remaining ? 'rimanente' : 'usato'}`);
            }
            if (stale && windows.length)
                group.add_child(label('!', 'qb-warning'));
            group.accessible_name = `${names[name]}${stale ? ': dati non aggiornati' : ''}`;
            this._box.add_child(group);
        }
        if (this._box.get_n_children() === 0)
            this._box.add_child(label('QuotaBar'));
        this._button.accessible_name = `${demo ? 'Dati dimostrativi. ' : ''}QuotaBar. ${descriptions.join('. ')}`;
        if (rebuildMenu)
            this._renderMenu();
    }

    _text(text, style = '') {
        const row = new PopupMenu.PopupBaseMenuItem({reactive: true, activate: false,
            hover: false, can_focus: false});
        row.remove_style_class_name('popup-inactive-menu-item');
        const textLabel = label(text, style);
        textLabel.clutter_text.line_wrap = true;
        textLabel.set_style('max-width: 340px;');
        row.add_child(textLabel);
        this._button.menu.addMenuItem(row);
    }

    _window(item) {
        const row = new PopupMenu.PopupBaseMenuItem({reactive: true, activate: false,
            hover: false, can_focus: false});
        row.remove_style_class_name('popup-inactive-menu-item');
        const column = new St.BoxLayout({vertical: true, style_class: 'qb-window', x_expand: true});
        const heading = new St.BoxLayout({x_expand: true});
        heading.add_child(label(item.label));
        const value = label(`${percent(item)} usato`, 'qb-number qb-menu-value');
        value.x_expand = true;
        value.x_align = Clutter.ActorAlign.END;
        heading.add_child(value);
        column.add_child(heading);
        column.add_child(bar(item.used, 310, 8));
        const reset = countdown(item.resets_at);
        column.add_child(label(expired(item) ? 'Reset raggiunto · attendo una nuova lettura' : `Reset tra ${reset}`, 'qb-muted'));
        row.add_child(column);
        const updateAccent = () => {
            // Read the uncolored native row, so the accent follows theme changes.
            const onDark = darkSurface(row);
            const meter = quotaMeter(item.used, false, onDark);
            const rgb = meter?.color.map(channel => Math.round(channel * 255)).join(', ');
            // Lift text slightly on dark surfaces to retain AA contrast on its tint.
            const textRgb = meter?.color.map(channel =>
                Math.round((onDark ? channel * 0.85 + 0.15 : channel) * 255)).join(', ');
            const surfaceStyle = rgb ? `background-color: rgba(${rgb}, 0.07);` : '';
            const valueStyle = textRgb ? `color: rgb(${textRgb});` : '';
            if (column.get_style() !== surfaceStyle)
                column.set_style(surfaceStyle);
            if (value.get_style() !== valueStyle)
                value.set_style(valueStyle);
        };
        row.connect('style-changed', updateAccent);
        row.connect('notify::mapped', () => {
            if (row.mapped)
                updateAccent();
        });
        this._button.menu.addMenuItem(row);
    }

    _renderMenu() {
        const menu = this._button.menu;
        const focused = global.stage.get_key_focus();
        const focusedLabel = menu._getMenuItems().includes(focused) ? focused.label?.text : null;
        menu.removeAll();
        this._text(this._data?.demo ? 'QuotaBar · dati dimostrativi' : 'QuotaBar', 'qb-menu-title');
        this._text('Quote di abbonamento · percentuali usate', 'qb-muted');
        if (this._message)
            this._text(this._message, 'qb-warning');
        for (const name of ['claude', 'codex']) {
            if (!this._settings.get_boolean(`show-${name}`))
                continue;
            menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
            this._text(names[name], 'qb-heading');
            const data = this._data?.providers?.[name];
            if (!data)
                this._text(this._process ? 'Lettura in corso…' : 'In attesa di dati', 'qb-muted');
            else {
                if (data.status === 'error')
                    this._text(data.error, 'qb-warning');
                this._text(age(data.observed_at), 'qb-muted');
                for (const item of [...(data.windows ?? []), ...(data.extra ?? [])])
                    this._window(item);
            }
        }
        menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());
        const refresh = new PopupMenu.PopupMenuItem(this._process ? 'Aggiornamento in corso…' : 'Aggiorna quote');
        refresh.setSensitive(!this._process);
        refresh.connect('activate', () => this._fetch(true));
        menu.addMenuItem(refresh);
        const settings = new PopupMenu.PopupMenuItem('Account e impostazioni…');
        settings.connect('activate', () => this.openPreferences());
        menu.addMenuItem(settings);
        if (focusedLabel && menu.isOpen) {
            const replacement = menu._getMenuItems().find(item => item.label?.text === focusedLabel);
            replacement?.grab_key_focus();
        }
    }

    disable() {
        this._generation = null;
        if (this._timer)
            GLib.source_remove(this._timer);
        this._timer = null;
        this._cancellable?.cancel();
        // The bounded helper finishes naturally; cancelling display must never
        // kill an unrelated CLI session or leave one of its app-servers orphaned.
        this._process = null;
        if (this._settingsId)
            this._settings.disconnect(this._settingsId);
        this._settingsId = null;
        this._settings = null;
        this._button?.destroy();
        this._button = null;
        this._box = null;
        this._data = null;
        this._cancellable = null;
        this._lastFetch = null;
        this._queuedFetch = false;
    }
}
