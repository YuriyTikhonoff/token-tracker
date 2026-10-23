#!/usr/bin/env bash
# Builds the extension, starts the fixture backend and opens a VS Code window that
# runs the extension against it. Closing that window stops the fixture.
#
#   npm run dev:host              # starts in the "on" scenario
#   npm run dev:host -- ahead     # or: on, reserve, limit, idle
#
# While it runs, switch scenarios from another terminal:
#   curl http://127.0.0.1:8799/scenario/limit
set -euo pipefail

cd "$(dirname "$0")/.."
scenario="${1:-on}"
port="${PORT:-8799}"

command -v code >/dev/null || { echo "The 'code' command is not in PATH. In VS Code: Cmd+Shift+P, 'Shell Command: Install code command in PATH'." >&2; exit 1; }

npm run build --silent

# A throwaway workspace whose settings point the extension at the fixture, so your own
# settings and your real backend are not touched. Your theme still applies.
workspace="$(mktemp -d)"
mkdir "$workspace/.vscode"
cat > "$workspace/.vscode/settings.json" <<JSON
{
  "tokenTracker.url": "http://127.0.0.1:$port",
  "tokenTracker.refreshSeconds": 10
}
JSON

PORT="$port" node test/fixture-server.mjs "$scenario" &
fixture=$!
trap 'kill "$fixture" 2>/dev/null || true; rm -rf "$workspace"' EXIT
sleep 1
kill -0 "$fixture" 2>/dev/null || { echo "The fixture did not start; is port $port taken? Try PORT=8797 npm run dev:host" >&2; exit 1; }

echo "Opening VS Code with the extension. Close that window to stop the fixture."
echo "Switch state: curl http://127.0.0.1:$port/scenario/<ahead|on|reserve|limit|idle> (the status bar follows within 10 seconds)"
code --wait --new-window --disable-extensions --extensionDevelopmentPath="$PWD" "$workspace"
