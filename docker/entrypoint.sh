#!/bin/sh
set -eu

cd /app

mkdir -p logs data/captures data/debug

if [ -n "${TIMEZONE:-}" ] && [ -f "/usr/share/zoneinfo/${TIMEZONE}" ]; then
    ln -snf "/usr/share/zoneinfo/${TIMEZONE}" /etc/localtime
    echo "${TIMEZONE}" > /etc/timezone
fi

case "${SERVICE_NAME:-}" in
    authserver)
        exec python authserver.py
        ;;
    worldserver)
        exec python worldserver.py
        ;;
    proxyserver)
        exec python proxyserver.py
        ;;
    admin_panel)
        exec python admin_panel/app.py
        ;;
    *)
        exec "$@"
        ;;
esac
