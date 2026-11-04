import json
import os
import subprocess
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from quotabar.cache import claude_auth_revision, display_provider, read_cache, snapshot, update_provider
from quotabar.model import normalize_claude, normalize_codex, window
from quotabar.providers import CodexRPC, NoRedirect, ProviderError, fetch_claude


class Normalization(unittest.TestCase):
    def test_codex_weekly_in_primary_is_not_mislabeled_five_hour(self):
        result = normalize_codex({"rateLimits": {"limitId": "codex", "primary": {
            "usedPercent": 28, "windowDurationMins": 10080, "resetsAt": 1900000000}}})
        self.assertEqual(result["windows"][0]["label"], "7g")
        self.assertEqual(len(result["windows"]), 1)

    def test_zero_is_valid_missing_is_not_zero(self):
        self.assertIsNone(window("x", "x", None, None))
        self.assertEqual(window("x", "x", 0, None)["used"], 0)
        for value in [False, float("nan"), float("inf"), "25"]:
            self.assertIsNone(window("x", "x", value, None))

    def test_codex_multi_bucket_and_unusual_window_duration(self):
        result = normalize_codex({"rateLimitsByLimitId": {
            "codex": {"limitId": "codex", "primary": {"usedPercent": 0, "windowDurationMins": 15}},
            "spark": {"limitName": "Spark", "primary": {"usedPercent": 37, "windowDurationMins": 60}},
        }})
        self.assertEqual(result["windows"][0]["label"], "15m")
        self.assertEqual(result["extra"][0]["label"], "Spark · 1h")

    def test_claude_models_and_null_windows(self):
        result = normalize_claude({"five_hour": None,
            "seven_day": {"utilization": 0, "resets_at": "2026-11-01T10:00:00Z"},
            "limits": [{"group": "weekly", "percent": 17,
                        "scope": {"model": {"display_name": "Fable"}}, "resets_at": None}]})
        self.assertEqual([item["label"] for item in result["windows"]], ["7g"])
        self.assertEqual(result["extra"][0]["label"], "Fable · 7g")
        self.assertGreater(result["windows"][0]["resets_at"], 0)

    def test_bad_model_fields_do_not_break_primary_windows(self):
        result = normalize_claude({"five_hour": {"utilization": 40},
                                   "limits": [None, {"scope": []}, {"scope": {"model": "bad"}}]})
        self.assertEqual(result["windows"][0]["used"], 40)
        self.assertEqual(result["extra"], [])


class CacheRules(unittest.TestCase):
    def test_rate_limit_display_explains_remaining_wait_without_exposing_old_usage(self):
        old = {"status": "error", "error_kind": "rate_limit", "retry_at": 1125,
               "observed_at": 900, "error": "Old generic message", "windows": [{"used": 83}]}
        for now, expected in ((1000, "3 min"), (1100, "25 s"), (1125, "a breve")):
            displayed = display_provider(old, 180, now)
            self.assertIn("HTTP 429", displayed["error"])
            self.assertIn(expected, displayed["error"])
            self.assertEqual(displayed["windows"], [])
        self.assertEqual(old["error"], "Old generic message")

    def test_cached_snapshot_follows_recovery_without_lock_write_or_provider_calls(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            cache_file = path / "usage.json"
            cache_file.write_text(json.dumps({"claude": {"status": "error", "error_kind": "rate_limit",
                "retry_at": 1125, "observed_at": 900, "windows": [{"used": 83}]}}))
            with patch("quotabar.cache.cache_directory", return_value=path), \
                    patch("quotabar.cache.time.time", return_value=1000), \
                    patch("quotabar.cache.fetch_claude") as fetch, \
                    patch("quotabar.cache.atomic_write") as write, \
                    patch("quotabar.cache.fcntl.flock") as lock:
                first = snapshot(only=["claude"], cached_only=True)
                cache_file.write_text(json.dumps({"claude": {"status": "ok", "observed_at": 990,
                    "windows": [{"used": 45}], "extra": []}}))
                second = snapshot(only=["claude"], cached_only=True)
            self.assertEqual(first["providers"]["claude"]["windows"], [])
            self.assertEqual(second["providers"]["claude"]["status"], "ok")
            self.assertNotIn("error", second["providers"]["claude"])
            self.assertEqual(second["providers"]["claude"]["windows"], [{"used": 45}])
            fetch.assert_not_called()
            write.assert_not_called()
            lock.assert_not_called()
            self.assertFalse((path / "usage.lock").exists())

    def test_claude_renewed_credentials_recover_from_hour_long_auth_backoff(self):
        for saved_revision in (None, "old-login"):
            old = {"status": "error", "error_kind": "auth", "observed_at": 100,
                   "retry_at": 10000, "failures": 7,
                   "windows": [{"used": 83}], "auth_revision": saved_revision}
            with patch("quotabar.cache.time.time", return_value=500):
                result = update_provider("claude", old,
                    lambda: {"windows": [{"used": 100}]}, 180, False, 500, "renewed-login")
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["windows"], [{"used": 100}])
            self.assertEqual(result["auth_revision"], "renewed-login")
            self.assertEqual(result["failures"], 0)

    def test_credential_change_does_not_bypass_provider_rate_limit(self):
        old = {"status": "error", "error_kind": "rate_limit", "retry_at": 1000,
               "observed_at": 100, "auth_revision": "old-login"}
        def never():
            self.fail("Credential changes must respect provider HTTP 429")
        self.assertEqual(update_provider("claude", old, never, 180, True, 900, "new-login"), old)

    def test_auth_errors_retry_in_one_minute_instead_of_one_hour(self):
        def expired():
            raise ProviderError("Sessione scaduta", "auth")
        result = update_provider("claude", {"failures": 7}, expired, 180, False, 1000)
        self.assertEqual(result["retry_at"], 1060)

    def test_auth_revision_observes_cli_file_changes_without_copying_secrets(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": directory}):
            self.assertEqual(claude_auth_revision(), "unavailable")
            path = Path(directory) / ".credentials.json"
            path.write_text("private-token-before")
            before = claude_auth_revision()
            path.write_text("private-token-after-renewal")
            after = claude_auth_revision()
            self.assertNotEqual(before, after)
            self.assertNotIn("private-token", before + after)

    def test_display_never_emits_error_or_stale_cached_percentages(self):
        for state in ({"status": "error", "error_kind": "auth", "observed_at": 990},
                      {"status": "error", "error_kind": "network", "observed_at": 990},
                      {"status": "ok", "observed_at": 100},
                      {"status": "ok", "observed_at": 2000}):
            old = {**state, "windows": [{"used": 83}], "extra": [{"used": 81}],
                   "auth_revision": "internal-file-revision"}
            result = display_provider(old, 180, 1000)
            self.assertEqual(result["windows"], [])
            self.assertEqual(result["extra"], [])
            self.assertNotIn("auth_revision", result)
            self.assertEqual(old["windows"], [{"used": 83}])

    def test_display_keeps_current_global_quota_and_drops_expired_window(self):
        live = {"status": "ok", "observed_at": 990, "windows": [
            {"id": "five_hour", "used": 35, "resets_at": 900},
            {"id": "seven_day", "used": 100, "resets_at": 2000}], "extra": []}
        result = display_provider(live, 180, 1000)
        self.assertEqual([item["used"] for item in result["windows"]], [100])

    def test_busy_cache_reader_hides_stale_values_and_disabled_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            (path / "usage.json").write_text(json.dumps({
                "claude": {"status": "error", "error_kind": "auth", "observed_at": 100,
                           "windows": [{"used": 83}], "extra": [], "auth_revision": "internal"},
                "codex": {"status": "ok", "observed_at": 990, "windows": [{"used": 77}]}}))
            with patch("quotabar.cache.cache_directory", return_value=path), \
                    patch("quotabar.cache.fcntl.flock", side_effect=BlockingIOError), \
                    patch("quotabar.cache.time.monotonic", side_effect=[0, 6]), \
                    patch("quotabar.cache.time.time", return_value=1000), \
                    patch("quotabar.cache.fetch_claude") as fetch:
                result = snapshot(only=["claude"])
            fetch.assert_not_called()
            self.assertEqual(list(result["providers"]), ["claude"])
            self.assertEqual(result["providers"]["claude"]["windows"], [])
            self.assertNotIn("auth_revision", result["providers"]["claude"])

    def test_manual_refresh_cannot_bypass_backoff(self):
        old = {"status": "error", "observed_at": 100, "retry_at": 1000}
        def never():
            self.fail("A provider under backoff must not be called")
        self.assertEqual(update_provider("claude", old, never, 180, True, 900), old)

    def test_manual_refresh_has_minimum_gap(self):
        old = {"status": "ok", "observed_at": 100}
        def never():
            self.fail("An eager manual click must use cached data")
        self.assertEqual(update_provider("claude", old, never, 180, True, 159), old)

    def test_error_preserves_last_success_without_fresh_timestamp(self):
        old = {"status": "ok", "observed_at": 100, "windows": [{"used": 28}], "extra": []}
        def offline():
            raise ProviderError("Offline", "network")
        result = update_provider("codex", old, offline, 60, False, 1000)
        self.assertEqual(result["observed_at"], 100)
        self.assertEqual(result["windows"], old["windows"])
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["retry_at"], 1060)

    def test_unknown_exception_is_sanitized(self):
        def fail():
            raise RuntimeError("Authorization: secret-test-token")
        result = update_provider("codex", {}, fail, 60, False, 1000)
        self.assertNotIn("secret-test-token", json.dumps(result))

    def test_snapshot_is_private_atomic_and_disabled_provider_is_not_called(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            value = {"windows": [{"id": "x", "label": "7g", "used": 28}], "extra": [], "plan": "Pro"}
            with patch("quotabar.cache.cache_directory", return_value=path), \
                    patch("quotabar.cache.fetch_codex", return_value=value) as codex, \
                    patch("quotabar.cache.fetch_claude") as claude:
                first = snapshot(only=["codex"])
                second = snapshot(only=["codex"])
            self.assertEqual(first["providers"]["codex"]["windows"], value["windows"])
            self.assertEqual(first["providers"], second["providers"])
            self.assertEqual(codex.call_count, 1)
            claude.assert_not_called()
            self.assertEqual((path / "usage.json").stat().st_mode & 0o777, 0o600)
            self.assertEqual(read_cache(path / "usage.json")["codex"]["plan"], "Pro")
            self.assertEqual(list(path.glob(".usage-*")), [])


class ProviderBoundaries(unittest.TestCase):
    def test_only_http_429_is_reported_as_a_usage_read_rate_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".credentials.json"
            path.write_text(json.dumps({"claudeAiOauth": {"accessToken": "dummy-local-fixture"}}))
            for code, kind in ((429, "rate_limit"), (401, "auth"), (503, "network")):
                error = urllib.error.HTTPError('https://api.anthropic.com/api/oauth/usage', code,
                    'Synthetic HTTP failure', {'Retry-After': '240'}, None)
                with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": directory}), \
                        patch("urllib.request.build_opener") as opener:
                    opener.return_value.open.side_effect = error
                    with self.assertRaises(ProviderError) as raised:
                        fetch_claude()
                self.assertEqual(raised.exception.kind, kind)
                self.assertEqual("HTTP 429" in str(raised.exception), code == 429)
                if code == 429:
                    self.assertEqual(raised.exception.retry_after, 240)

    def test_http_authorization_never_follows_redirect(self):
        self.assertIsNone(NoRedirect().redirect_request(None, None, 302, "Moved", {}, "https://other.invalid"))

    def test_expired_claude_token_is_not_sent_or_modified(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".credentials.json"
            content = json.dumps({"claudeAiOauth": {"accessToken": "dummy-expired", "expiresAt": 1}})
            path.write_text(content)
            with patch.dict(os.environ, {"CLAUDE_CONFIG_DIR": directory}), \
                    patch("urllib.request.build_opener") as opener:
                with self.assertRaises(ProviderError) as error:
                    fetch_claude()
                self.assertEqual(error.exception.kind, "auth")
                opener.assert_not_called()
            self.assertEqual(path.read_text(), content)

    def test_rpc_handles_buffered_notifications_and_cleans_child(self):
        fake = '''#!/usr/bin/python3
import sys,json
for line in sys.stdin:
    message=json.loads(line)
    if 'id' not in message: continue
    notice={'method':'test/notification','params':{}}
    response={'id':message['id'],'result':{'ok':True}}
    sys.stdout.write(json.dumps(notice)+'\\n'+json.dumps(response)+'\\n');sys.stdout.flush()
'''
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "codex"
            path.write_text(fake)
            path.chmod(0o700)
            with patch("quotabar.providers.executable", return_value=str(path)):
                with CodexRPC() as rpc:
                    process = rpc.process
                    self.assertEqual(rpc.request("account/rateLimits/read"), {"ok": True})
            self.assertIsNotNone(process.poll())


if __name__ == "__main__":
    unittest.main()
