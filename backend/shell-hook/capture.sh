# Token Tracker — manual terminal command capture (zsh).
#
# Appends "<iso8601-timestamp>\t<cwd>\t<command>" to commands.log for every
# command you type interactively. Does NOT capture command output, only the
# command line itself.
#
# Install (not done automatically — this edits your shell startup):
#   echo "source $PWD/backend/shell-hook/capture.sh" >> ~/.zshrc     # run from the repo root
# then open a new terminal (or `source ~/.zshrc`).
#
# Uninstall: remove that line from ~/.zshrc.

_token_tracker_source="${BASH_SOURCE[0]:-$0}"
_token_tracker_backend="$(cd "$(dirname "$_token_tracker_source")/.." && pwd)"
_token_tracker_log="${TOKEN_TRACKER_LOG:-$_token_tracker_backend/commands.log}"

_token_tracker_preexec() {
  local timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  printf '%s\t%s\t%s\n' "$timestamp" "$PWD" "$1" >> "$_token_tracker_log"
}

autoload -Uz add-zsh-hook 2>/dev/null
if typeset -f add-zsh-hook > /dev/null; then
  add-zsh-hook preexec _token_tracker_preexec
else
  preexec() { _token_tracker_preexec "$1"; }
fi
