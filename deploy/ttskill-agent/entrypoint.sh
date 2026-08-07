#!/bin/sh
set -eu

mkdir -p "$TTSKILL_HOME"

exec dbus-run-session -- sh -c '
  set -eu
  eval "$(gnome-keyring-daemon --start --components=secrets)"
  exec "$TTSKILL_BIN" "$@"
' sh "$@"
