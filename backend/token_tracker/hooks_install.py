"""Install and remove the Claude Code hooks that record which account a
session runs under (see hook.py and accounts.py).

Edits `<claude dir>/settings.json` in place, keeps everything else in it, and
leaves a timestamped backup next to it before writing.
"""
import json
import shlex
import shutil
from datetime import datetime
from pathlib import Path

from . import config

EVENTS = ("SessionStart", "UserPromptSubmit")
# A command counts as ours when it runs one of these scripts. record_account.py
# is the path older installs used.
MARKERS = ("token_tracker/hook.py", "token_tracker\\hook.py", "record_account.py")
HOOK_SCRIPT = Path(__file__).resolve().with_name("hook.py")


class SettingsError(Exception):
    pass


def settings_path() -> Path:
    return config.claude_dir() / "settings.json"


def hook_command() -> str:
    # The hook is stdlib-only, so any python3 will do; it is run by path so it
    # works wherever the package was installed.
    return f"python3 {shlex.quote(str(HOOK_SCRIPT))}"


def _is_ours(command) -> bool:
    return isinstance(command, str) and any(marker in command for marker in MARKERS)


def _entries_with_ours(entries):
    for entry in entries or []:
        for hook in entry.get("hooks", []) if isinstance(entry, dict) else []:
            if _is_ours(hook.get("command")):
                yield entry, hook


def load_settings(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SettingsError(f"cannot read {path}: {error}") from error
    if not isinstance(data, dict):
        raise SettingsError(f"{path} does not contain a JSON object")
    return data


def installed_events(settings: dict) -> list:
    hooks = settings.get("hooks") or {}
    return [event for event in EVENTS if any(_entries_with_ours(hooks.get(event)))]


def _write(path: Path, settings: dict) -> Path | None:
    backup = None
    if path.exists():
        backup = path.with_name(f"{path.name}.bak-token-tracker-{datetime.now():%Y%m%d%H%M%S}")
        shutil.copy2(path, backup)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(settings, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return backup


def install(dry_run=False) -> list:
    """Add the hooks that are missing. Returns the events that were added."""
    path = settings_path()
    settings = load_settings(path)
    hooks = settings.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise SettingsError(f"'hooks' in {path} is not an object")
    added = []
    for event in EVENTS:
        entries = hooks.setdefault(event, [])
        if any(_entries_with_ours(entries)):
            continue
        entries.append({"hooks": [{"type": "command", "command": hook_command()}]})
        added.append(event)
    if added and not dry_run:
        backup = _write(path, settings)
        if backup:
            print(f"Backed up {path} to {backup.name}")
    return added


def uninstall(dry_run=False) -> list:
    """Remove our hooks. Returns the events they were removed from."""
    path = settings_path()
    settings = load_settings(path)
    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        return []
    removed = []
    for event in EVENTS:
        entries = hooks.get(event)
        if not isinstance(entries, list):
            continue
        kept = []
        for entry in entries:
            inner = entry.get("hooks", []) if isinstance(entry, dict) else None
            if inner is None:
                kept.append(entry)
                continue
            remaining = [hook for hook in inner if not _is_ours(hook.get("command"))]
            if len(remaining) != len(inner):
                if event not in removed:
                    removed.append(event)
            if remaining:
                kept.append({**entry, "hooks": remaining})
        if kept:
            hooks[event] = kept
        else:
            hooks.pop(event, None)
    if not hooks:
        settings.pop("hooks", None)
    if removed and not dry_run:
        backup = _write(path, settings)
        if backup:
            print(f"Backed up {path} to {backup.name}")
    return removed
