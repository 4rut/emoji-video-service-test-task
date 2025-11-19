#!/bin/sh
set -e

uvicorn app.main:app --host "${APP_HOST:-0.0.0.0}" --port "${APP_PORT:-8000}" &
APP_PID=$!

BOT_PID=""
if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
    python -m app.bot &
    BOT_PID=$!
else
    echo "TELEGRAM_BOT_TOKEN is not set. Telegram bot will not start." >&2
fi

cleanup() {
    kill "$APP_PID" 2>/dev/null || true
    if [ -n "$BOT_PID" ]; then
        kill "$BOT_PID" 2>/dev/null || true
    fi
}

trap cleanup INT TERM

EXIT_CODE=0
while true; do
    if ! kill -0 "$APP_PID" 2>/dev/null; then
        wait "$APP_PID"
        EXIT_CODE=$?
        break
    fi
    if [ -n "$BOT_PID" ]; then
        if ! kill -0 "$BOT_PID" 2>/dev/null; then
            wait "$BOT_PID"
            EXIT_CODE=$?
            break
        fi
    fi
    sleep 1
done

cleanup
exit "$EXIT_CODE"
