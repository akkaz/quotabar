#!/bin/sh
set -eu
task_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
glib-compile-schemas --strict "$task_root/extension/schemas"
exec /usr/bin/python3 "$task_root/extension/helper.py" "$@"
