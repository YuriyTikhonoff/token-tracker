"""The `token-tracker` command."""
import argparse
import sys

COMMANDS = {
    "ingest": ("read new Claude Code transcripts into the database", "ingest"),
    "snapshot": ("record the subscription limits (needs the claude CLI)", "usage_snapshot"),
    "report": ("print a text report", "report"),
    "codex": ("read new Codex CLI sessions into the database", "codex_ingest"),
}


def _serve(args) -> int:
    import uvicorn

    if args.host not in ("127.0.0.1", "localhost", "::1"):
        print(
            "Warning: the API has no login. Anyone who can reach this address can read your "
            "usage history, including prompt previews.",
            file=sys.stderr,
        )
    print(f"Token Tracker on http://{args.host}:{args.port}")
    uvicorn.run("token_tracker.main:app", host=args.host, port=args.port)
    return 0


def _install_hooks(args) -> int:
    from . import hooks_install

    added = hooks_install.install(dry_run=args.dry_run)
    where = hooks_install.settings_path()
    if added:
        verb = "Would add" if args.dry_run else "Added"
        print(f"{verb} hooks for {', '.join(added)} in {where}.")
    else:
        print(f"Hooks are already installed in {where}.")
    return 0


def _uninstall_hooks(args) -> int:
    from . import hooks_install

    removed = hooks_install.uninstall(dry_run=args.dry_run)
    where = hooks_install.settings_path()
    if removed:
        verb = "Would remove" if args.dry_run else "Removed"
        print(f"{verb} hooks for {', '.join(removed)} in {where}.")
    else:
        print(f"No token-tracker hooks found in {where}.")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="token-tracker", description="Claude Code usage statistics, from your own logs.")
    sub = parser.add_subparsers(dest="command", metavar="<command>")

    serve = sub.add_parser("serve", help="run the dashboard and API")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8765)
    serve.set_defaults(run=_serve)

    for name, (help_text, _module) in COMMANDS.items():
        sub.add_parser(name, help=help_text, add_help=False)  # dispatched in main()

    for name, handler, help_text in (
        ("install-hooks", _install_hooks, "add the Claude Code hooks that record which account is in use"),
        ("uninstall-hooks", _uninstall_hooks, "remove those hooks"),
    ):
        hooks = sub.add_parser(name, help=help_text)
        hooks.add_argument("--dry-run", action="store_true", help="show what would change, write nothing")
        hooks.set_defaults(run=handler)

    sub.add_parser("doctor", help="check the setup and say what is missing")
    sub.add_parser("hook", help="(called by Claude Code) record the account of a session")
    return parser


def main(argv=None) -> int:
    from .schema import SchemaTooNewError

    try:
        return _main(sys.argv[1:] if argv is None else argv)
    except SchemaTooNewError as error:
        print(f"token-tracker: {error}", file=sys.stderr)
        return 2


def _main(argv) -> int:
    # Lightweight path first: Claude Code runs `hook` before every prompt.
    if argv[:1] == ["hook"]:
        from . import hook

        hook.main()
        return 0

    # These commands own their options; hand everything after the name over
    # untouched (argparse's REMAINDER drops a leading --option).
    if argv[:1] and argv[0] in COMMANDS:
        import importlib

        module = importlib.import_module(f"token_tracker.{COMMANDS[argv[0]][1]}")
        module.main(argv[1:])
        return 0

    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 0
    if args.command == "doctor":
        from . import doctor

        return doctor.run()
    return args.run(args)


if __name__ == "__main__":
    sys.exit(main())
