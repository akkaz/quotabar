#!/usr/bin/env bash
# Run a synthetic popup in a separate bus/compositor, never the user's desktop.
set -euo pipefail
if [[ "${QUOTABAR_SMOKE_ISOLATED:-}" != 1 ]]; then
    smoke_root="$(mktemp -d "${TMPDIR:-/tmp}/quotabar-gnome-smoke.XXXXXX")"
    export QUOTABAR_SMOKE_ROOT="$smoke_root" QUOTABAR_SMOKE_ISOLATED=1
    export XDG_CONFIG_HOME="$smoke_root/config" XDG_DATA_HOME="$smoke_root/data"
    export XDG_CACHE_HOME="$smoke_root/cache" XDG_RUNTIME_DIR="$smoke_root/runtime"
    export GSETTINGS_BACKEND=dconf
    mkdir -p "$XDG_CONFIG_HOME" "$XDG_DATA_HOME" "$XDG_CACHE_HOME" "$XDG_RUNTIME_DIR"
    chmod 700 "$XDG_RUNTIME_DIR"
    unset DISPLAY WAYLAND_DISPLAY
    exec dbus-run-session -- bash "$0"
fi

uuid=quotabar@akkaz.dev
extension="${QUOTABAR_SMOKE_EXTENSION_DIR:-/usr/share/gnome-shell/extensions/$uuid}"
if [[ -n "${QUOTABAR_SMOKE_EXTENSION_DIR:-}" ]]; then
    mkdir -p "$XDG_DATA_HOME/gnome-shell/extensions/$uuid"
    cp -a "$extension/." "$XDG_DATA_HOME/gnome-shell/extensions/$uuid/"
    extension="$XDG_DATA_HOME/gnome-shell/extensions/$uuid"
fi
export QUOTABAR_SMOKE_RESULT="$QUOTABAR_SMOKE_ROOT/result.json"
export XDG_CURRENT_DESKTOP=GNOME XDG_SESSION_TYPE=wayland LIBGL_ALWAYS_SOFTWARE=1
probe="$XDG_DATA_HOME/gnome-shell/extensions/quotabar-smoke@test.invalid"
mkdir -p "$probe"
cat > "$probe/metadata.json" <<'EOF'
{"uuid":"quotabar-smoke@test.invalid","name":"QuotaBar isolated test","description":"Synthetic CI probe","shell-version":["48","49","50","51"]}
EOF
cat > "$probe/extension.js" <<'EOF'
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import St from 'gi://St';
import {Extension} from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

export default class Probe extends Extension {
    enable() {
        let attempts = 0;
        const write = data => Gio.File.new_for_path(GLib.getenv('QUOTABAR_SMOKE_RESULT'))
            .replace_contents(JSON.stringify(data), null, false, Gio.FileCreateFlags.PRIVATE, null);
        this._source = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 1, () => {
            attempts++;
            try {
                const button = Main.panel.statusArea['quotabar@akkaz.dev'];
                if (button) {
                    button.menu.open();
                    const labels = [];
                    const visit = actor => {
                        if (actor instanceof St.Label)
                            labels.push(actor.text);
                        for (const child of actor.get_children())
                            visit(child);
                    };
                    visit(button.menu.actor);
                    if (labels.some(text => text.includes('dimostrativi')) &&
                        labels.includes('Claude') && labels.includes('Codex') &&
                        labels.some(text => text.includes('44%'))) {
                        write({ok: true, labels});
                        this._source = 0;
                        return GLib.SOURCE_REMOVE;
                    }
                }
                if (attempts < 35)
                    return GLib.SOURCE_CONTINUE;
                write({ok: false, error: 'Synthetic QuotaBar popup did not become ready'});
            } catch (error) {
                write({ok: false, error: String(error), stack: error.stack});
            }
            this._source = 0;
            return GLib.SOURCE_REMOVE;
        });
    }
    disable() {
        if (this._source)
            GLib.source_remove(this._source);
        this._source = 0;
    }
}
EOF

gsettings --schemadir "$extension/schemas" set org.gnome.shell.extensions.quotabar demo-mode true
gsettings set org.gnome.shell disable-user-extensions false
gsettings set org.gnome.shell enabled-extensions "['$uuid', 'quotabar-smoke@test.invalid']"
gnome-shell --headless --wayland --virtual-monitor 1280x720 --sm-disable > "$QUOTABAR_SMOKE_ROOT/shell.log" 2>&1 &
shell_pid=$!
trap 'kill "$shell_pid" 2>/dev/null || true' EXIT
for ((i=0; i<80; i++)); do
    if (( i % 5 == 0 )); then
        gnome-extensions enable "$uuid" 2>/dev/null || true
        gnome-extensions enable quotabar-smoke@test.invalid 2>/dev/null || true
    fi
    if [[ -f "$QUOTABAR_SMOKE_RESULT" ]]; then
        python3 - "$QUOTABAR_SMOKE_RESULT" <<'PY'
import json,sys
result=json.load(open(sys.argv[1]))
print(json.dumps(result,ensure_ascii=False))
sys.exit(0 if result.get('ok') else 1)
PY
        exit "$?"
    fi
    if ! kill -0 "$shell_pid" 2>/dev/null; then
        cat "$QUOTABAR_SMOKE_ROOT/shell.log"
        exit 1
    fi
    sleep 1
done
cat "$QUOTABAR_SMOKE_ROOT/shell.log"
gnome-extensions info "$uuid" || true
gnome-extensions info quotabar-smoke@test.invalid || true
gsettings get org.gnome.shell enabled-extensions
echo "QuotaBar GNOME smoke test timed out: $QUOTABAR_SMOKE_ROOT" >&2
exit 1
