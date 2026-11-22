#!/usr/bin/env bash
# Jalankan dari Termux/Android (file start.bat untuk Windows)
cd "$(dirname "$0")" || exit 1
PORT="${PORT:-8787}"

# Tahan wake lock agar device tidak sleep saat server jalan
if command -v termux-wake-lock >/dev/null 2>&1; then
  termux-wake-lock
  trap 'termux-wake-unlock 2>/dev/null || true' EXIT INT TERM
fi

echo "Starting OpenCode Account Manager..."
python3 server.py &
SERVER_PID=$!
sleep 1
if command -v termux-open-url >/dev/null 2>&1; then
  termux-open-url "http://127.0.0.1:${PORT}/" >/dev/null 2>&1 &
  termux-open-url "http://127.0.0.1:5173/" >/dev/null 2>&1 &
  termux-open-url "https://openrouter.ai/" >/dev/null 2>&1 &
fi
wait "$SERVER_PID"