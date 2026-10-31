#!/usr/bin/python3
import pathlib
import subprocess
import tempfile

root = pathlib.Path(__file__).resolve().parents[1]
subprocess.run(["/usr/bin/python3", "-m", "unittest", "discover", "-s", "tests", "-v"], cwd=root, check=True)
subprocess.run(["gjs", "-m", "tests/presentation.test.js"], cwd=root, check=True)
subprocess.run(["gjs", "-m", "tests/ui-import.test.js"], cwd=root, check=True)
with tempfile.TemporaryDirectory(prefix="quotabar-schema-") as directory:
    subprocess.run(["glib-compile-schemas", "--strict", "--targetdir", directory,
                    str(root / "extension/schemas")], check=True)
print("Backend, presentazione, import GTK e schema: OK")
