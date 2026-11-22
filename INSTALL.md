<div align="center">

# ⚡ Cara Install — Termux AI Gateway Setup ☠️

Panduan lengkap memasang stack gateway AI di Termux dari nol.

[![Kembali ke README](https://img.shields.io/badge/←_README-termux--ai--gateway--setup-7B61FF?style=for-the-badge)](README.md)

</div>

---

## 1. Prasyarat

```bash
pkg update -y
pkg install -y bash curl git nodejs-lts python3 termux-tools util-linux
```

Izinkan popup **Allow** saat diminta akses storage.

> Pakai Termux dari **F-Droid / GitHub**, bukan Play Store (versi Play Store sudah usang).

---

## 2. Pasang OpenCode

```bash
npm install -g opencode-ai
opencode --version
```

---

## 3. Clone repo

```bash
cd $HOME
git clone https://github.com/blukutupluk/termux-ai-gateway-setup.git
cd termux-ai-gateway-setup
bash install.sh
```

Atau manual:

```bash
cp -r bin/* "$HOME/bin/"
cp -r src/* "$HOME/src/"
cp -r shortcuts/* "$HOME/.shortcuts/"
cp -r config/opencode/tools/* "$HOME/.config/opencode/tools/"
cp config/opencode/opencode.example.json "$HOME/.config/opencode/opencode.json"
cp bashrc.example "$HOME/.bashrc"

chmod +x "$HOME/bin/"* "$HOME/.shortcuts/"*
```

---

## 4. Isi API key

Edit `~/.config/opencode/opencode.json`, ganti placeholder:

| Placeholder | Dapat dari |
|-------------|------------|
| `YOUR_API_KEY_HERE` | [OpenRouter](https://openrouter.ai/keys), [NVIDIA](https://build.nvidia.com/) |
| `YOUR_OPENROUTER_API_KEY` | https://openrouter.ai/keys |

Contoh key OpenRouter: `sk-or-v1-...`
Contoh key NVIDIA: `nvapi-...`

---

## 5. Pasang Termux:Widget

1. Install **Termux:Widget** dari F-Droid.
2. Di home screen: **long press → Widgets → Termux:Widget**.
3. Pilih shortcut `sambungopencode` (atau `FreeLLMAPI`).
4. Tap widget → semua service langsung nyala. ☠️

---

## 6. Verifikasi

```bash
~/bin/start-all-services

for p in 3000 3001 5173 8787; do
  printf "port $p: "
  curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:$p/
done
```

Harus keluar semua `HTTP 200`.

Buka dashboard:

```bash
termux-open-url http://127.0.0.1:8787   # Account Manager
termux-open-url http://127.0.0.1:5173   # FreeLLMAPI Dashboard
```

---

## 7. Auto-start saat Termux dibuka

File `~/.bashrc` sudah memanggil `start-all-services` otomatis. Jadi dua skenario sama-sama works:

- **Tap widget** → script dipanggil langsung dari widget.
- **Buka Termux biasa** → `.bashrc` yang memanggil.

---

## Troubleshooting

| Masalah | Solusi |
|---------|--------|
| `ECONNREFUSED` di OpenCode | `~/bin/start-all-services`, lalu cek port |
| Port 5173 mati | `npm run build -w client` di `~/freellmapi` |
| `tsx: not found` | pakai path lengkap `~/freellmapi/node_modules/.bin/tsx` |
| Proses mati lagi | pastikan `setsid` terpasang: `pkg install util-linux` |
| `localhost` tidak bisa di browser | pakai `127.0.0.1`, jangan `localhost` |
| Widget tidak muncul | reinstall Termux:Widget dari F-Droid |

---

<div align="center">

**☠️ Selesai — tap widget, semua provider nyala.**

</div>
