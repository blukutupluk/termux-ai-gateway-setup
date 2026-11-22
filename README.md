# termux-opencode-stack

Backup konfigurasi & script untuk stack OpenCode + multi-provider di Termux (Android).

## Isi
- `bin/start-all-services` — script master, nyalakan semua service sekaligus (wake lock + setsid)
- `bin/keymanager`, `bin/opencode-account`, `bin/sambungopencode`, `bin/freellmapi-launcher` — CLI & launcher
- `src/` — source Key Manager (proxy OpenRouter / Groq / DeepSeek / Gemini / Together)
- `shortcuts/` — script Termux:Widget (taruh di `~/.shortcuts/`)
- `config/opencode/tools/opencode-account-manager/` — dashboard manajemen akun (port 8787)
- `config/opencode/opencode.example.json` — contoh config provider (API key di-redact)
- `bashrc.example` — contoh `.bashrc` (API key di-redact)

## Service & Port
| Service | Port |
|---------|------|
| Key Manager (proxy multi-provider) | 3000 |
| freellmapi server | 3001 |
| freellmapi dashboard | 5173 |
| OpenCode Account Manager | 8787 |

## Instalasi cepat
1. Copy isi folder ini ke lokasi sesuai struktur di atas.
2. `chmod +x bin/* shortcuts/*`
3. Isi API key di `~/.config/opencode/opencode.json` (dari `opencode.example.json`).
4. Tap widget `sambungopencode` atau jalankan `~/bin/start-all-services`.

Semua proses pakai `setsid` + `termux-wake-lock` agar tetap hidup walau layar mati / widget ditutup.

## Log
Semua log terpusat di `~/.local/log/services/`.
