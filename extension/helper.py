#!/usr/bin/python3
"""Self-contained helper for both .deb and extension ZIP installs."""
import os
import sys
from pathlib import Path

extension = Path(__file__).resolve().parent
os.environ["QUOTABAR_EXTENSION"] = str(extension)
sys.path.insert(0, str(extension / "backend" if (extension / "backend").is_dir() else extension.parent))
from quotabar.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
