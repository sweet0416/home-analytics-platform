#!/bin/sh
set -eu

mkdir -p "$TTSKILL_HOME"

# Keep one D-Bus/keyring session alive for the opt-in sidecar. The official
# CLI uses Secret Service on Linux, so recreating the session for every
# invocation would lose the login context.
SESSION_ENV="$TTSKILL_HOME/session.env"

if [ "${1:-}" = "daemon" ]; then
  exec dbus-run-session -- sh -c '
    set -eu
    # Create the persistent login collection before starting Secret Service.
    printf "\\n" | gnome-keyring-daemon --login --components=secrets >/dev/null 2>&1 || true
    eval "$(gnome-keyring-daemon --start --components=secrets)"
    printf "export DBUS_SESSION_BUS_ADDRESS=%s\\n" "$DBUS_SESSION_BUS_ADDRESS" > "$TTSKILL_HOME/session.env"
    printf "export GNOME_KEYRING_CONTROL=%s\\n" "${GNOME_KEYRING_CONTROL:-}" >> "$TTSKILL_HOME/session.env"
    trap "rm -f \"$TTSKILL_HOME/session.env\"" EXIT TERM INT
    while :; do sleep 3600; done
  '
fi

if [ -f "$SESSION_ENV" ]; then
  # shellcheck disable=SC1090
  . "$SESSION_ENV"
  exec "$TTSKILL_BIN" "$@"
fi

exec dbus-run-session -- sh -c '
  set -eu
  printf "\\n" | gnome-keyring-daemon --login --components=secrets >/dev/null 2>&1 || true
  eval "$(gnome-keyring-daemon --start --components=secrets)"
  exec "$TTSKILL_BIN" "$@"
' sh "$@"
