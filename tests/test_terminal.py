import unittest
from unittest.mock import patch

from quotabar.cli import login, terminal_command
from quotabar.providers import ProviderError


class TerminalLaunch(unittest.TestCase):
    def test_debian_keeps_the_users_terminal_alternative(self):
        with patch("quotabar.cli.shutil.which", return_value="/usr/bin/x-terminal-emulator"):
            self.assertEqual(terminal_command(["python3", "path with spaces"]),
                             ["/usr/bin/x-terminal-emulator", "-e", "python3", "path with spaces"])

    def test_fedora_uses_ptyxis_with_literal_arguments(self):
        with patch("quotabar.cli.shutil.which", side_effect=lambda name:
                   "/usr/bin/ptyxis" if name == "ptyxis" else None):
            self.assertEqual(terminal_command(["python3", "/a b/helper.py", "_login", "claude"]),
                ["/usr/bin/ptyxis", "--standalone", "--", "python3", "/a b/helper.py", "_login", "claude"])

    def test_console_and_gnome_terminal_fallbacks(self):
        for terminal in ("kgx", "gnome-terminal"):
            with patch("quotabar.cli.shutil.which", side_effect=lambda name:
                       f"/usr/bin/{terminal}" if name == terminal else None):
                self.assertEqual(terminal_command(["python3"]), [f"/usr/bin/{terminal}", "--", "python3"])

    def test_missing_terminal_is_actionable(self):
        with patch("quotabar.cli.shutil.which", return_value=None):
            with self.assertRaises(ProviderError) as error:
                terminal_command(["python3"])
            self.assertEqual(error.exception.kind, "missing_terminal")

    def test_login_only_launches_official_cli_helper_without_a_shell(self):
        with patch("quotabar.cli.executable", return_value="/usr/bin/claude"), \
                patch("quotabar.cli.terminal_command", return_value=["ptyxis", "--", "helper"]) as terminal, \
                patch("quotabar.cli.subprocess.Popen") as spawn:
            login("claude", "/a b/helper.py")
            terminal.assert_called_once_with(["/usr/bin/python3", "/a b/helper.py", "_login", "claude"])
            self.assertEqual(spawn.call_args.args[0], ["ptyxis", "--", "helper"])
            self.assertNotIn("shell", spawn.call_args.kwargs)
