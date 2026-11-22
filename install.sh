#!/data/data/com.termux/files/usr/bin/bash
# install.sh — pasang Termux AI Gateway Setup ke $HOME
# Dipakai oleh: git clone ... && bash install.sh

set -uo pipefail
export PATH="/data/data/com.termux/files/usr/bin:$PATH"

SRC="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

echo "☠️  Termux AI Gateway Setup — installer"
echo "────────────────────────────────────────"

# 1. Dependency dasar
echo "[1/6] Cek dependency..."
for cmd in curl git node npm python3 setsid; do
  command -v "$cmd" >/dev/null 2>&1 || echo "  ⚠ $cmd belum ada (pkg install $cmd)"
done

# 2. Folder
echo "[2/6] Siapkan folder..."
mkdir -p "$HOME/bin" "$HOME/src" "$HOME/.shortcuts" \
         "$HOME/.config/opencode/tools" "$HOME/.local/log/services"

# 3. Copy file
echo "[3/6] Copy script & config..."
cp -f "$SRC"/bin/*        "$HOME/bin/"        2>/dev/null
cp -f "$SRC"/src/*.js     "$HOME/src/"        2>/dev/null
cp -r  "$SRC"/src/routes  "$HOME/src/"        2>/dev/null
cp -f "$SRC"/shortcuts/*  "$HOME/.shortcuts/" 2>/dev/null
cp -r  "$SRC"/config/opencode/tools/* \
                          "$HOME/.config/opencode/tools/" 2>/dev/null

# 4. Config (jangan timpa yang sudah ada)
if [ ! -f "$HOME/.config/opencode/opencode.json" ]; then
  cp "$SRC/config/opencode/opencode.example.json" \
     "$HOME/.config/opencode/opencode.json"
  echo "  ✓ opencode.json dibuat dari contoh (isi API key kamu!)"
else
  echo "  ✓ opencode.json sudah ada, tidak ditimpa"
fi

if [ ! -f "$HOME/.bashrc" ] || ! grep -q "start-all-services" "$HOME/.bashrc"; then
  cp "$SRC/bashrc.example" "$HOME/.bashrc"
  echo "  ✓ .bashrc dipasang"
else
  echo "  ✓ .bashrc sudah ada auto-start, tidak ditimpa"
fi

# 5. Permission
echo "[4/6] Permission..."
chmod +x "$HOME/bin/"* "$HOME/.shortcuts/"* 2>/dev/null

# 6. Wake lock + jalankan
echo "[5/6] Aktifkan wake lock & jalankan service..."
command -v termux-wake-lock >/dev/null 2>&1 && termux-wake-lock
"$HOME/bin/start-all-services"

# 7. Selesai
echo "[6/6] Verifikasi..."
for p in 3000 3001 5173 8787; do
  printf "  port %s: " "$p"
  curl -s --max-time 2 -o /dev/null -w "%{http_code}\n" http://127.0.0.1:$p/ 2>&1
done

echo ""
echo "✅ Selesai! Lanjut ke:"
echo "   • https://github.com/blukutupluk/termux-ai-gateway-setup#-cara-install"
echo "   • isi API key di ~/.config/opencode/opencode.json"
echo "   • tap widget sambungopencode di home screen ☠️"
