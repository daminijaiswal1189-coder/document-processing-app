"""Paths and runtime limits. Override output with MOA_OUTPUT_DIR (use K: drive in production)."""

from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_DIR = ROOT / "config"
OUTPUT_DIR = Path(os.environ.get("MOA_OUTPUT_DIR", ROOT / "output")).expanduser()
LOG_DIR = ROOT / "logs"
TEMPLATES_DIR = ROOT / "templates"

MAX_FILES = 80
MAX_FILE_BYTES = 50 * 1024 * 1024
HOST = os.environ.get("MOA_HOST", "127.0.0.1")
PORT = int(os.environ.get("MOA_PORT", "8002"))
