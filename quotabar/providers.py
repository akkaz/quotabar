"""Read usage only. No inference, conversation, or remote write methods."""

import json
import os
import selectors
import shutil
import signal
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from . import __version__
from .model import normalize_claude, normalize_codex


class ProviderError(Exception):
    def __init__(self, message, kind="network", retry_after=0):
        super().__init__(message)
        self.kind = kind
        self.retry_after = retry_after


def executable(name):
    found = shutil.which(name)
    if found:
        return found
    for directory in (".local/bin", ".npm-global/bin", ".cargo/bin"):
        candidate = Path.home() / directory / name
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate)
    raise ProviderError(f"Installa {name} per collegare il tuo account.", "missing_cli")


class CodexRPC:
    """Bounded JSON-lines RPC client for the official local app-server."""

    def __init__(self):
        self.process = None
        self.pending = b""
        self.counter = 0

    def __enter__(self):
        self.deadline = time.monotonic() + 22
        self.process = subprocess.Popen(
            [executable("codex"), "app-server", "--listen", "stdio://"],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        try:
            self.request("initialize", {"clientInfo": {
                "name": "quotabar", "title": "QuotaBar", "version": __version__}})
            self.send({"method": "initialized"})
        except Exception:
            self.close()
            raise
        return self

    def send(self, message):
        try:
            self.process.stdin.write((json.dumps(message) + "\n").encode())
            self.process.stdin.flush()
        except (OSError, BrokenPipeError) as error:
            raise ProviderError("Codex si è chiuso. Aggiorna la CLI e riprova.", "cli") from error

    def request(self, method, params=None, timeout=18):
        self.counter += 1
        request_id = self.counter
        self.send({"id": request_id, "method": method, "params": params or {}})
        deadline = min(self.deadline, time.monotonic() + timeout)
        with selectors.DefaultSelector() as selector:
            selector.register(self.process.stdout, selectors.EVENT_READ)
            while time.monotonic() < deadline:
                while b"\n" in self.pending:
                    line, self.pending = self.pending.split(b"\n", 1)
                    try:
                        response = json.loads(line)
                    except (ValueError, UnicodeError):
                        continue
                    if response.get("id") != request_id:
                        continue
                    if "error" in response:
                        # Never forward arbitrary provider errors: they can carry
                        # request details, headers, or account identifiers.
                        raise ProviderError("Codex non riesce a leggere le quote. Verifica il login.", "auth")
                    return response.get("result") or {}
                if not selector.select(max(0, deadline - time.monotonic())):
                    break
                chunk = os.read(self.process.stdout.fileno(), 65536)
                if not chunk:
                    raise ProviderError("Codex si è chiuso durante la lettura.", "cli")
                self.pending += chunk
                if len(self.pending) > 2_000_000:
                    raise ProviderError("Risposta Codex non valida.", "format")
        raise ProviderError("Codex non risponde. Riprova tra poco.", "timeout")

    def close(self):
        if not self.process:
            return
        # Only our isolated process group, never other Codex sessions.
        try:
            os.killpg(self.process.pid, signal.SIGTERM)
            self.process.wait(timeout=2)
        except ProcessLookupError:
            pass
        except subprocess.TimeoutExpired:
            try:
                os.killpg(self.process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            self.process.wait()
        for stream in (self.process.stdin, self.process.stdout):
            if stream:
                stream.close()
        self.process = None

    def __exit__(self, *_):
        self.close()


def fetch_codex():
    with CodexRPC() as rpc:
        account = rpc.request("account/read", {"refreshToken": False}).get("account")
        if not account:
            raise ProviderError("Collega il tuo account ChatGPT.", "auth")
        if account.get("type") != "chatgpt":
            raise ProviderError("Le quote di abbonamento richiedono il login con ChatGPT.", "unsupported")
        result = normalize_codex(rpc.request("account/rateLimits/read"))
        if not result.get("plan"):
            result["plan"] = account.get("planType")
    if not result["windows"]:
        raise ProviderError("Questo account non espone finestre di utilizzo Codex.", "unsupported")
    return result


class NoRedirect(urllib.request.HTTPRedirectHandler):
    """Do not forward an Authorization header to a redirected origin."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def fetch_claude():
    directory = Path(os.environ.get("CLAUDE_CONFIG_DIR", str(Path.home() / ".claude")))
    try:
        content = (directory / ".credentials.json").read_text()
        if len(content) > 1_000_000:
            raise ValueError("oversize")
        auth = json.loads(content).get("claudeAiOauth") or {}
    except FileNotFoundError as error:
        raise ProviderError("Collega Claude Code per leggere le quote.", "auth") from error
    except (OSError, ValueError, AttributeError) as error:
        raise ProviderError("Le credenziali Claude non sono leggibili. Ripeti il login.", "auth") from error
    token = auth.get("accessToken")
    if not isinstance(token, str) or not token:
        raise ProviderError("Collega un abbonamento Claude, anziché una chiave API.", "auth")
    expiry = auth.get("expiresAt")
    if isinstance(expiry, (int, float)) and expiry / 1000 <= time.time():
        raise ProviderError("Sessione Claude scaduta. Apri Claude Code o ripeti il login.", "auth")
    request = urllib.request.Request("https://api.anthropic.com/api/oauth/usage", headers={
        "Authorization": "Bearer " + token, "Accept": "application/json",
        "anthropic-beta": "oauth-2025-04-20", "User-Agent": f"QuotaBar/{__version__}",
    })
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=12) as response:
            payload = response.read(1_000_001)
        if len(payload) > 1_000_000:
            raise ValueError("oversize")
        result = normalize_claude(json.loads(payload), auth.get("subscriptionType"))
    except urllib.error.HTTPError as error:
        if error.code in (401, 403):
            raise ProviderError("Claude richiede un nuovo login.", "auth") from error
        if error.code == 429:
            try:
                retry = min(3600, max(180, int(error.headers.get("Retry-After", "180"))))
            except (TypeError, ValueError):
                retry = 180
            raise ProviderError("Lettura quote Claude in pausa (HTTP 429).", "rate_limit", retry) from error
        raise ProviderError(f"Claude non disponibile (HTTP {error.code}).", "network") from error
    except (ValueError, AttributeError, TypeError) as error:
        raise ProviderError("Il formato delle quote Claude è cambiato.", "format") from error
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ProviderError("Claude non raggiungibile. Controlla la connessione.", "network") from error
    if not result["windows"]:
        raise ProviderError("Questo account non espone quote di abbonamento Claude.", "unsupported")
    return result
