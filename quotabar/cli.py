"""Command-line entry point, also used by the GNOME extension."""

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

from . import __version__
from .cache import snapshot, cache_directory, atomic_write, read_cache
from .providers import ProviderError, executable


def demo():
    now = time.time()
    def provider(windows, extra=()):
        def row(key, label, used, remaining, duration):
            return {"id": key, "label": label, "used": used,
                    "resets_at": now + remaining, "duration_minutes": duration}
        return {"status": "ok", "observed_at": now, "plan": "Demo",
                "windows": [row(*item) for item in windows],
                "extra": [row(*item) for item in extra]}
    return {"version": 1, "demo": True, "generated_at": now, "providers": {
        "claude": provider([("five_hour", "5h", 44, 13320, 300),
                             ("seven_day", "7g", 24, 417600, 10080)],
                            [("model:0", "Fable · 7g", 17, 417600, 10080)]),
        "codex": provider([("primary", "7g", 28, 410400, 10080)]),
    }}


def terminal_command(argv):
    # Debian's alternatives launcher is absent on Fedora Workstation.
    for name, flags in (("x-terminal-emulator", ["-e"]),
                        ("ptyxis", ["--standalone", "--"]),
                        ("kgx", ["--"]), ("gnome-terminal", ["--"])):
        terminal = shutil.which(name)
        if terminal:
            return [terminal, *flags, *argv]
    raise ProviderError("Installa Ptyxis, Console o GNOME Terminal per collegare l’account.", "missing_terminal")


def login(provider, helper):
    # Launch the unmodified official CLI: browser login, refresh, storage, and
    # any required verification are owned by the provider.
    executable(provider)
    subprocess.Popen(terminal_command(["/usr/bin/python3", helper, "_login", provider]),
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                     stderr=subprocess.DEVNULL, start_new_session=True)


def login_in_terminal(provider):
    command = [executable(provider)]
    command += ["login"] if provider == "codex" else ["auth", "login", "--claudeai"]
    print(f"QuotaBar · collega {provider.title()}\n")
    result = subprocess.run(command, check=False)
    if result.returncode == 0:
        # A successful explicit sign-in should not wait for an old error's backoff.
        import fcntl
        directory = cache_directory()
        with open(directory / "usage.lock", "a") as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            state = read_cache(directory / "usage.json")
            state.pop(provider, None)
            atomic_write(directory / "usage.json", state)
        print("\nAccount collegato. La barra si aggiornerà automaticamente.")
    else:
        print("\nLogin non completato. Puoi riprovare da QuotaBar.")
    if sys.stdin.isatty():
        try:
            input("Premi Invio per chiudere.")
        except EOFError:
            pass
    return result.returncode


def main():
    parser = argparse.ArgumentParser(prog="quotabar", description="Quote Codex e Claude nella barra di GNOME")
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command")
    usage = commands.add_parser("snapshot", help="Emetti solo quote e stato in JSON, mai credenziali")
    usage.add_argument("--refresh", action="store_true")
    usage.add_argument("--demo", action="store_true")
    usage.add_argument("--only", choices=("codex", "claude", "both"), default="both")
    usage.add_argument("--codex-interval", type=int, default=60)
    usage.add_argument("--claude-interval", type=int, default=180)
    for name in ("login", "_login"):
        sub = commands.add_parser(name, help="Collega un account con la CLI ufficiale")
        sub.add_argument("provider", choices=("codex", "claude"))
    commands.add_parser("settings", help="Apri la configurazione grafica")
    args = parser.parse_args()
    extension = Path(os.environ["QUOTABAR_EXTENSION"])
    helper = str(extension / "helper.py")
    try:
        if args.command == "snapshot":
            value = demo() if args.demo else snapshot(args.refresh, args.codex_interval,
                                                       args.claude_interval,
                                                       None if args.only == "both" else [args.only])
            print(json.dumps(value, ensure_ascii=False, allow_nan=False))
        elif args.command == "login":
            login(args.provider, helper)
        elif args.command == "_login":
            return login_in_terminal(args.provider)
        else:
            os.execv("/usr/bin/gjs", ["gjs", "-m", str(extension / "setup.js"), helper])
    except ProviderError as error:
        print(str(error), file=sys.stderr)
        return 1
    except (OSError, ValueError):
        print("QuotaBar non riesce ad avviarsi. Verifica l’installazione e riprova.", file=sys.stderr)
        return 1
    return 0
