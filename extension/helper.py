#!/usr/bin/python3
"""Self-contained helper for native packages and extension ZIP installs."""
import os
import sys
from pathlib import Path

# Native package directories must stay owned entirely by the package manager,
# including when an administrator runs --version. Do not leave untracked .pyc
# files that would keep those directories around after package removal.
sys.dont_write_bytecode = True

extension = Path(__file__).resolve().parent
os.environ["QUOTABAR_EXTENSION"] = str(extension)
sys.path.insert(0, str(extension / "backend" if (extension / "backend").is_dir() else extension.parent))
from quotabar.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
