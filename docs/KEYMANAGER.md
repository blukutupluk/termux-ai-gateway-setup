# API Key Manager untuk OpenCode

Server lokal di Termux untuk mengelola banyak API key gratis dengan **auto-failover** saat kena rate limit.

## Akses Dashboard (PENTING)

Server berjalan di port `3000`. Buka di browser HP dengan alamat:

```
http://127.0.0.1:3000
```

> **Gunakan `127.0.0.1`, jangan `localhost`.** Di Android, `localhost` sering di-resolve ke IPv6 (`::1`) atau kena proxy/VPN sehingga gagal dibuka.

Dari **device lain** (PC/laptop) yang satu WiFi, gunakan IP LAN HP:

```
http://192.168.0.100:3000
```

IP LAN bisa berubah setiap kali HP reconnect WiFi. Cek IP terbaru dengan:

```bash
keymanager url
```

## Menjalankan Server

```bash
# Cara paling mudah (launcher, background)
keymanager start

# Cara manual
npm start
# atau
node bin/cli.js --port=3000
```

Perintah lain:

```bash
keymanager stop     # matikan server
keymanager doctor   # cek konektivitas + deteksi VPN
keymanager url      # tampilkan URL akses
```

## Cek Konektivitas

```bash
npm run doctor
```

Contoh hasil sehat:

```
1. Loopback (127.0.0.1:3000)  : ✅ OK
2. LAN IP (192.168.0.100:3000): ✅ OK
3. VPN aktif                   : ✅ tidak ada
```

### Kalau tetap gagal dibuka

1. **VPN aktif (tun0/Clash/WireGuard dll)** — paling sering menyebabkan browser tidak bisa mengakses alamat LAN/loopback.
   - Tambahkan rule **bypass / DIRECT** untuk `127.0.0.0/8` dan `192.168.0.0/16` di app VPN, atau
   - Matikan VPN sesaat, lalu buka `http://127.0.0.1:3000`.
   Termux biasanya sudah ter-exclude dari VPN, makanya `curl` dari Termux sukses tapi browser HP gagal.

2. **Salah IP** — IP WiFi bisa berubah (misal dari `192.168.50.220` jadi `192.168.0.100`). Selalu cek dengan `keymanager url`.

3. **AP Isolation di router** — matikan fitur *WiFi Isolation / Guest Network* agar device bisa saling mengakses.

## Menambah API Key

1. Buka `http://127.0.0.1:3000`
2. Klik **Add Key**
3. Pilih provider (OpenRouter / Groq / DeepSeek / Gemini / Together)
4. Masukkan nama & API key
5. Simpan

Key yang sudah **rate limit (429)** otomatis masuk cooldown 60 detik, lalu proxy memakai key berikutnya. Key **invalid (401/403)** otomatis di-disable.

## Integrasi OpenCode

```bash
npm run setup-opencode
```

Ini menambahkan provider `local-manager` ke `~/.config/opencode/opencode.json` (backup otomatis dibuat).

Lalu pakai model dengan format `provider/model`:

```
groq/llama-3.3-70b-versatile
gemini/gemini-2.5-flash
openrouter/google/gemini-2.5-flash
```

## Kelola Akun OpenCode Console

Skrip `opencode-account` memakai **CLI resmi** `opencode auth` (aman, tidak menulis SQLite manual):

```bash
opencode-account add                        # tambah akun baru (login device flow)
opencode-account list                       # lihat akun + email + status aktif
opencode-account switch [label]             # ganti akun aktif (picker kalau kosong)
opencode-account add-import <file.json>     # import dari backup
opencode-account export [file.json]         # backup credential (izin 0600)
opencode-account remove <label>             # hapus akun
```

Contoh hasil `opencode-account list`:

```
LABEL     EMAIL               ORG       STATUS  ID
Personal  adpram01@gmail.com  Personal  AKTIF  cred_1f6ab...
adpram01  adpram01@gmail.com  adpram01  -      cred_1fe4c...
```

> Token akses **tidak pernah** ditampilkan di `list` atau log. File `export` berisi rahasia — jangan dibagikan.

## Endpoint API

| Endpoint | Keterangan |
|----------|------------|
| `GET /v1/models` | Daftar provider aktif (format OpenAI) |
| `POST /v1/chat/completions` | Proxy chat + auto-failover (streaming didukung) |
| `GET /api/keys` | List API key |
| `POST /api/keys` | Tambah API key |
| `PUT /api/keys/:id` | Update key |
| `DELETE /api/keys/:id` | Hapus key |
| `GET /api/stats` | Statistik penggunaan |
| `GET /health` | Health check |

## Test

```bash
npm test
```

## File Penting

- `data/db.json` — penyimpanan API key & status
- `/data/data/com.termux/files/usr/tmp/opencode/keymanager.log` — log server
