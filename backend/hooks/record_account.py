#!/usr/bin/env python3
"""Thin entry point kept at its old path so hooks installed before the package
existed keep working. The logic lives in token_tracker/hook.py."""
import runpy
from pathlib import Path

runpy.run_path(str(Path(__file__).resolve().parent.parent / "token_tracker" / "hook.py"), run_name="__main__")
